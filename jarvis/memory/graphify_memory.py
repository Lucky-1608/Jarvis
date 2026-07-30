from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import networkx as nx
import structlog
from rapidfuzz import process as fuzz_process, fuzz

from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.config.settings import get_settings

logger = structlog.get_logger(__name__)


class GraphifyMemory:
    """Knowledge graph memory backed by Graphify + NetworkX."""
    
    def __init__(self, data_dir: str):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._graph_path = self._data_dir / "graph.json"
        self._graph: Optional[nx.DiGraph] = None
        self._bus = get_event_bus()
    
    async def initialize(self) -> None:
        """Load existing graph.json if available."""
        self._load_graph()
    
    def _load_graph(self) -> bool:
        """Load graph.json into NetworkX DiGraph. Returns True if loaded."""
        if not self._graph_path.exists():
            logger.info("Graph file not found", path=str(self._graph_path))
            return False
            
        try:
            with open(self._graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Using node_link_graph to load from standardized networkx format
            self._graph = nx.node_link_graph(data, directed=True, multigraph=False)
            logger.info("Graph loaded successfully", 
                        nodes=self._graph.number_of_nodes(), 
                        edges=self._graph.number_of_edges())
            return True
        except Exception as e:
            logger.error("Failed to load graph", error=str(e), exc_info=True)
            return False
    
    def is_available(self) -> bool:
        """Check if a graph has been loaded."""
        return self._graph is not None and len(self._graph) > 0
    
    async def build(self, target_dir: str) -> dict:
        """Build knowledge graph from a directory using graphify CLI."""
        logger.info("Building knowledge graph", target_dir=target_dir)
        cmd = ["graphify", target_dir, "--out", str(self._data_dir)]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error("Graphify build failed", stderr=stderr.decode('utf-8', errors='replace'))
                return {"status": "error", "message": stderr.decode('utf-8', errors='replace')}
            
            success = self._load_graph()
            if success:
                # Need to use standard getattr for EventTypes to avoid potential crashes 
                # if the specific event doesn't exist yet, but per prompt instruction we publish it.
                event_type = getattr(EventTypes, "GRAPH_BUILT", "graph_built")
                await self._bus.publish(Event(
                    type=event_type,
                    data={"target_dir": target_dir},
                    source="graphify",
                ))
            
            return self.get_stats()
        except FileNotFoundError:
            logger.warning("Graphify CLI not found. Is it installed?")
            return {"status": "error", "message": "Graphify CLI not found"}
    
    async def update(self, target_dir: str) -> dict:
        """Incremental update — re-extract only changed files."""
        logger.info("Updating knowledge graph", target_dir=target_dir)
        cmd = ["graphify", "update", target_dir, "--out", str(self._data_dir)]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error("Graphify update failed", stderr=stderr.decode('utf-8', errors='replace'))
                return {"status": "error", "message": stderr.decode('utf-8', errors='replace')}
            
            success = self._load_graph()
            if success:
                event_type = getattr(EventTypes, "GRAPH_UPDATED", "graph_updated")
                await self._bus.publish(Event(
                    type=event_type,
                    data={"target_dir": target_dir},
                    source="graphify",
                ))
            
            return self.get_stats()
        except FileNotFoundError:
            logger.warning("Graphify CLI not found. Is it installed?")
            return {"status": "error", "message": "Graphify CLI not found"}
    
    def explain(self, node_id: str) -> dict | None:
        """Explain a node: type, file, line, community, degree, connections."""
        if not self.is_available():
            return None
            
        resolved_id = self._resolve_node_id(node_id)
        if not resolved_id:
            return None
            
        node_data = dict(self._graph.nodes[resolved_id])
        
        connections = []
        for neighbor in self._graph.neighbors(resolved_id):
            edge_data = self._graph.get_edge_data(resolved_id, neighbor, default={})
            connections.append({
                "neighbor": neighbor,
                "relation": edge_data.get("relation", "unknown"),
                "direction": "out"
            })
        for predecessor in self._graph.predecessors(resolved_id):
            edge_data = self._graph.get_edge_data(predecessor, resolved_id, default={})
            connections.append({
                "neighbor": predecessor,
                "relation": edge_data.get("relation", "unknown"),
                "direction": "in"
            })
            
        return {
            "id": resolved_id,
            "attributes": node_data,
            "degree": self._graph.degree(resolved_id),
            "in_degree": self._graph.in_degree(resolved_id),
            "out_degree": self._graph.out_degree(resolved_id),
            "connections": connections
        }
    
    def find_path(self, source: str, target: str) -> list[dict] | None:
        """Find shortest path between two entities."""
        if not self.is_available():
            return None
            
        src_id = self._resolve_node_id(source)
        tgt_id = self._resolve_node_id(target)
        
        if not src_id or not tgt_id:
            return None
            
        undirected_graph = self._graph.to_undirected()
        try:
            path = nx.shortest_path(undirected_graph, src_id, tgt_id)
            result = []
            for i in range(len(path)):
                node = path[i]
                step = {"node": node, "attributes": self._graph.nodes[node]}
                if i < len(path) - 1:
                    next_node = path[i+1]
                    if self._graph.has_edge(node, next_node):
                        step["edge_to_next"] = self._graph.get_edge_data(node, next_node)
                        step["direction"] = "out"
                    elif self._graph.has_edge(next_node, node):
                        step["edge_to_next"] = self._graph.get_edge_data(next_node, node)
                        step["direction"] = "in"
                result.append(step)
            return result
        except nx.NetworkXNoPath:
            return None
    
    def query_neighbors(self, node_id: str, depth: int = 1) -> dict:
        """Get node neighborhood subgraph up to depth."""
        if not self.is_available():
            return {}
            
        resolved_id = self._resolve_node_id(node_id)
        if not resolved_id:
            return {}
            
        subgraph = nx.ego_graph(self._graph, resolved_id, radius=depth, undirected=True)
        return nx.node_link_data(subgraph)
    
    def search_entities(self, query: str, limit: int = 10) -> list[dict]:
        """Fuzzy text search over node labels/IDs."""
        if not self.is_available():
            return []
            
        nodes = list(self._graph.nodes())
        results = fuzz_process.extract(query, nodes, limit=limit, scorer=fuzz.WRatio)
        
        matches = []
        for match, score, index in results:
            node_data = self._graph.nodes[match]
            matches.append({
                "id": match,
                "score": score,
                "attributes": node_data
            })
        return matches
    
    def get_community(self, community_id: int) -> list[dict]:
        """Get all nodes in a Leiden community cluster."""
        if not self.is_available():
            return []
            
        community_nodes = []
        for node, data in self._graph.nodes(data=True):
            if data.get("community") == community_id:
                community_nodes.append({
                    "id": node,
                    "attributes": data
                })
        return community_nodes
    
    def get_stats(self) -> dict:
        """Return graph statistics."""
        if not self.is_available():
            return {"status": "unavailable"}
            
        communities = set()
        for _, data in self._graph.nodes(data=True):
            if "community" in data:
                communities.add(data["community"])
                
        return {
            "status": "available",
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
            "communities": len(communities),
            "graph_path": str(self._graph_path)
        }
    
    def _resolve_node_id(self, query: str) -> str | None:
        """Resolve a fuzzy query to an exact node ID."""
        if not self.is_available():
            return None
            
        # Exact match
        if query in self._graph:
            return query
            
        # Case-insensitive match
        query_lower = query.lower()
        for node in self._graph.nodes():
            if str(node).lower() == query_lower:
                return node
                
        # Substring match
        for node in self._graph.nodes():
            if query_lower in str(node).lower():
                return node
                
        # Fuzzy match
        nodes = list(self._graph.nodes())
        match = fuzz_process.extractOne(query, nodes, scorer=fuzz.WRatio)
        if match and match[1] > 70:  # Threshold for fuzzy match
            return match[0]
            
        return None
    
    def get_context_for_query(self, query: str, max_entities: int = 5) -> str:
        """Format graph context as markdown for LLM prompt injection.
        
        This is called by ContextManager.build_messages() to inject
        knowledge graph context into the system prompt.
        """
        if not self.is_available():
            return ""
            
        top_matches = self.search_entities(query, limit=max_entities)
        if not top_matches:
            return ""
            
        lines = ["### Knowledge Graph Context"]
        for match in top_matches:
            node_id = match["id"]
            attrs = match["attributes"]
            node_type = attrs.get("type", "unknown")
            file_path = attrs.get("file", "unknown")
            
            lines.append(f"\n- **Entity**: `{node_id}` (type: {node_type}, file: {file_path})")
            
            connections = []
            out_edges = self._graph.out_edges(node_id, data=True)
            for u, v, data in out_edges:
                rel = data.get("relation", "relates_to")
                connections.append(f"{rel} {v}")
                
            if connections:
                lines.append(f"  - **Connections**: {', '.join(connections[:10])}")
                if len(connections) > 10:
                    lines.append(f"  - *(...and {len(connections) - 10} more)*")
                    
        return "\n".join(lines)
