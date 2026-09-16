"""Payment Graph — the network model that accumulates value with every node.

Every node = payment rail, provider, country, currency, merchant, receiver, settlement method
Every edge = "money can potentially move from A -> B under these conditions"

The routing engine solves: find the valid, compliant, economical path through the graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Currency, PaymentMethod
from .providers import ProviderRegistry


@dataclass
class GraphNode:
    id: str
    node_type: str  # "provider", "rail", "country", "currency", "receiver", "merchant"
    label: str
    metadata: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str  # "supports", "converts", "settles_to", "routes_via"
    weight: float = 1.0
    metadata: dict = field(default_factory=dict)


class PaymentGraph:
    """The payment routing graph that grows with every receiver/merchant added."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self.registry = registry or ProviderRegistry()
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._adjacency: dict[str, list[GraphEdge]] = {}
        self._build_from_registry()

    def _build_from_registry(self) -> None:
        """Build initial graph from registered providers."""
        # Add currency nodes
        for currency in Currency:
            node = GraphNode(
                id=f"currency:{currency.value}",
                node_type="currency",
                label=currency.value,
            )
            self._nodes[node.id] = node

        # Add provider nodes and edges
        for provider in self.registry.all():
            provider_node = GraphNode(
                id=f"provider:{provider.id}",
                node_type="provider",
                label=provider.name,
                metadata={
                    "settlement_speed": provider.settlement_speed.value,
                    "api_latency_ms": provider.api_latency_ms,
                },
            )
            self._nodes[provider_node.id] = provider_node

            # Edge: provider supports currency
            for currency in provider.supported_currencies:
                self._add_edge(
                    source=provider_node.id,
                    target=f"currency:{currency.value}",
                    edge_type="supports",
                    weight=1.0,
                )

            # Edge: provider supports payment method -> currency
            for method in provider.supported_methods:
                method_node_id = f"method:{method.value}"
                if method_node_id not in self._nodes:
                    self._nodes[method_node_id] = GraphNode(
                        id=method_node_id,
                        node_type="method",
                        label=method.value,
                    )
                self._add_edge(
                    source=provider_node.id,
                    target=method_node_id,
                    edge_type="supports",
                    weight=provider.get_success_rate(method),
                )

        # Add country nodes
        countries = ["IN", "US", "EU", "SG", "AE", "NP", "BD", "LK"]
        for c in countries:
            self._nodes[f"country:{c}"] = GraphNode(
                id=f"country:{c}",
                node_type="country",
                label=c,
            )

        # Cross-border edges (simplified)
        corridors = [
            ("IN", "SG"), ("IN", "AE"), ("IN", "US"),
            ("IN", "NP"), ("IN", "BD"), ("IN", "LK"),
            ("US", "EU"), ("US", "SG"), ("EU", "SG"),
        ]
        for src, dst in corridors:
            self._add_edge(
                source=f"country:{src}",
                target=f"country:{dst}",
                edge_type="corridor",
                weight=0.95,
                metadata={"bidirectional": True},
            )

    def _add_edge(self, source: str, target: str, edge_type: str, weight: float = 1.0, metadata: dict | None = None) -> None:
        edge = GraphEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            weight=weight,
            metadata=metadata or {},
        )
        self._edges.append(edge)
        self._adjacency.setdefault(source, []).append(edge)

    def add_receiver(self, receiver_id: str, country: str, methods: list[PaymentMethod], currency: Currency) -> str:
        """Add a receiver node to the graph. Returns the node ID."""
        node_id = f"receiver:{receiver_id}"
        node = GraphNode(
            id=node_id,
            node_type="receiver",
            label=receiver_id,
            metadata={
                "country": country,
                "methods": [m.value for m in methods],
                "currency": currency.value,
            },
        )
        self._nodes[node_id] = node

        # Connect receiver to their country
        country_id = f"country:{country}"
        if country_id in self._nodes:
            self._add_edge(node_id, country_id, "located_in", 1.0)

        # Connect receiver to their payment methods
        for method in methods:
            method_id = f"method:{method.value}"
            if method_id in self._nodes:
                self._add_edge(node_id, method_id, "accepts", 1.0)

        # Connect receiver to their currency
        currency_id = f"currency:{currency.value}"
        if currency_id in self._nodes:
            self._add_edge(node_id, currency_id, "denominated_in", 1.0)

        return node_id

    def add_merchant(self, merchant_id: str, country: str, methods: list[PaymentMethod], currency: Currency) -> str:
        """Add a merchant node to the graph."""
        node_id = f"merchant:{merchant_id}"
        node = GraphNode(
            id=node_id,
            node_type="merchant",
            label=merchant_id,
            metadata={
                "country": country,
                "methods": [m.value for m in methods],
                "currency": currency.value,
            },
        )
        self._nodes[node_id] = node

        country_id = f"country:{country}"
        if country_id in self._nodes:
            self._add_edge(node_id, country_id, "located_in", 1.0)

        for method in methods:
            method_id = f"method:{method.value}"
            if method_id in self._nodes:
                self._add_edge(node_id, method_id, "accepts", 1.0)

        return node_id

    def find_path(self, source_id: str, target_id: str, max_depth: int = 4) -> list[GraphEdge] | None:
        """BFS to find a path between two nodes."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        visited = {source_id}
        queue = [(source_id, [])]

        for _ in range(max_depth):
            next_queue = []
            for node_id, path in queue:
                for edge in self._adjacency.get(node_id, []):
                    neighbor = edge.target if edge.source == node_id else edge.source
                    if neighbor == target_id:
                        return path + [edge]
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_queue.append((neighbor, path + [edge]))
            queue = next_queue

        return None

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def stats(self) -> dict:
        type_counts: dict[str, int] = {}
        for node in self._nodes.values():
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1
        edge_type_counts: dict[str, int] = {}
        for edge in self._edges:
            edge_type_counts[edge.edge_type] = edge_type_counts.get(edge.edge_type, 0) + 1
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types": type_counts,
            "edge_types": edge_type_counts,
        }
