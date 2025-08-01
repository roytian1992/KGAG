"""
图数据库存储模块

基于Neo4j的知识图谱存储
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
import json

from ..models.entities import KnowledgeGraph, Entity, Relation
from ..utils.config import KAGConfig


class GraphStore:
    """图数据库存储"""
    
    def __init__(self, config: KAGConfig):
        self.config = config
        self.driver = None
        self._connect()
    
    def _connect(self) -> None:
        """连接到Neo4j数据库"""
        try:
            self.driver = GraphDatabase.driver(
                self.config.storage.neo4j_uri,
                auth=(
                    self.config.storage.neo4j_username,
                    self.config.storage.neo4j_password
                )
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✅ Neo4j连接成功")
        except Exception as e:
            print(f"❌ Neo4j连接失败: {str(e)}")
            self.driver = None
    
    def store_knowledge_graph(self, kg: KnowledgeGraph) -> None:
        """存储知识图谱"""
        if not self.driver:
            print("⚠️ Neo4j未连接，跳过图存储")
            return
        
        with self.driver.session() as session:
            # 清空现有数据（可选）
            session.run("MATCH (n) DETACH DELETE n")
            
            # 存储实体
            for entity in kg.entities.values():
                # print(f"存储实体: {entity}")
                self._store_entity(session, entity)
            
            # 存储关系
            for relation in kg.relations.values():
                # print(f"存储关系: {relation}")
                self._store_relation(session, relation)
    
    def _store_entity(self, session, entity: Entity) -> None:
        """存储单个实体"""
        query = f"""
        MERGE (e:{entity.type} {{id: $id}})
        SET e.name = $name,
            e.type = $type,
            e.aliases = $aliases,
            e.description = $description,
            e.properties = $properties,
            e.source_chunks = $source_chunks
        """
        try:
            properties = json.dumps(entity.properties, ensure_ascii=False)
            session.run(query, {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "aliases": entity.aliases,
                "description": entity.description,
                "properties": properties,
                # "confidence": entity.confidence,
                "source_chunks": entity.source_chunks
            })

        except Exception as e:
            print(f"[Neo4j] MERGE Entity 失败: {e}")

    
    def _store_relation(self, session, relation: Relation) -> None:
        """存储单个关系"""
        query = f"""
        MATCH (s {{id: $subject_id}})
        MATCH (o {{id: $object_id}})
        MERGE (s)-[r:{relation.predicate} {{id: $id}}]->(o)
        SET r.predicate = $predicate,
            r.properties = $properties,
            r.source_chunks = $source_chunks
        """
        try:
            properties = json.dumps(relation.properties, ensure_ascii=False)
            session.run(query, {
                "id": relation.id,
                "subject_id": relation.subject_id,
                "object_id": relation.object_id,
                "predicate": relation.predicate,
                "properties": properties,
                # "confidence": relation.confidence,
                "source_chunks": relation.source_chunks
            })

        except Exception as e:
            print(f"[Neo4j] MERGE Relation 失败: {e}")

    
    def search_entities(self, query: str, limit: int = 10) -> List[Entity]:
        """搜索实体"""
        if not self.driver:
            return []
        
        with self.driver.session() as session:
            cypher_query = """
            MATCH (e:Entity)
            WHERE e.name CONTAINS $query OR any(alias IN e.aliases WHERE alias CONTAINS $query)
            RETURN e
            LIMIT $limit
            """
            
            result = session.run(cypher_query, {"query": query, "limit": limit})
            entities = []
            
            for record in result:
                entity_data = record["e"]
                properties = json.loads(entity_data.get("properties", "{}"))
                entity = Entity(
                    id=entity_data["id"],
                    name=entity_data["name"],
                    type=entity_data["type"],
                    aliases=entity_data.get("aliases", []),
                    description=entity_data.get("description"),
                    properties=properties,
                    source_chunks=entity_data.get("source_chunks", [])
                )
                entities.append(entity)
            
            return entities
    
    def search_relations(self, entity_name: str, limit: int = 10) -> List[Relation]:
        """搜索关系"""
        if not self.driver:
            return []
        
        with self.driver.session() as session:
            cypher_query = """
            MATCH (s:Entity)-[r:RELATION]->(o:Entity)
            WHERE s.name = $entity_name OR o.name = $entity_name
            RETURN r, s.id as subject_id, o.id as object_id
            LIMIT $limit
            """
            
            result = session.run(cypher_query, {"entity_name": entity_name, "limit": limit})
            relations = []
            
            for record in result:
                relation_data = record["r"]
                relation = Relation(
                    id=relation_data["id"],
                    subject_id=record["subject_id"],
                    object_id=record["object_id"],
                    predicate=relation_data["predicate"],
                    properties=json.loads(relation_data.get("properties", "{}")),
                    source_chunks=relation_data.get("source_chunks", [])
                )
                relations.append(relation)
            
            return relations
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.driver:
            return {"status": "disconnected"}
        
        with self.driver.session() as session:
            # 统计实体数量
            entity_count = session.run("MATCH (e:Entity) RETURN count(e) as count").single()["count"]
            
            # 统计关系数量
            relation_count = session.run("MATCH ()-[r:RELATION]->() RETURN count(r) as count").single()["count"]
            
            return {
                "status": "connected",
                "entities": entity_count,
                "relations": relation_count
            }
    
    def close(self) -> None:
        """关闭连接"""
        if self.driver:
            self.driver.close()

