"""
Dependency Graph Builder with Kahn's Algorithm.
Handles parallel execution planning and deadlock detection.
"""

from __future__ import annotations
from typing import Optional
from collections import deque
from .models import ExecutionStep, DependencyType


class DependencyGraph:
    """
    Dependency graph for execution steps.
    Supports Kahn's algorithm for topological sort and parallel execution grouping.
    """

    def __init__(self):
        self.nodes: dict[str, ExecutionStep] = {}
        self.edges_from: dict[str, list[str]] = {}  # adjacency list: node -> list of dependent nodes
        self.edges_to: dict[str, list[str]] = {}   # reverse: node -> list of prerequisites
        self.dependency_types: dict[tuple[str, str], DependencyType] = {}

    def add_step(self, step: ExecutionStep) -> None:
        """Add a step to the graph."""
        self.nodes[step.step_id] = step
        self.edges_from.setdefault(step.step_id, [])
        self.edges_to.setdefault(step.step_id, [])

        # Add explicit dependencies
        for dep_id in step.dependencies:
            self.add_dependency(dep_id, step.step_id, DependencyType.DATA)

    def add_dependency(
        self,
        from_step: str,
        to_step: str,
        dep_type: DependencyType,
    ) -> None:
        """Add a dependency between steps."""
        if from_step not in self.nodes or to_step not in self.nodes:
            return

        if from_step not in self.edges_from:
            self.edges_from[from_step] = []
        if to_step not in self.edges_to:
            self.edges_to[to_step] = []

        if to_step not in self.edges_from[from_step]:
            self.edges_from[from_step].append(to_step)
            self.edges_to[to_step].append(from_step)
            self.dependency_types[(from_step, to_step)] = dep_type

    def get_dependencies(self, step_id: str) -> list[str]:
        """Get direct dependencies of a step."""
        return self.edges_to.get(step_id, []).copy()

    def get_dependents(self, step_id: str) -> list[str]:
        """Get direct dependents of a step."""
        return self.edges_from.get(step_id, []).copy()

    def topological_sort(self) -> list[list[str]]:
        """
        Kahn's algorithm for topological sort.
        Returns parallel execution groups (steps that can run concurrently).

        Each group is a list of step IDs that can execute in parallel.
        Groups are ordered - group[0] must complete before group[1], etc.
        """
        # Calculate in-degree for each node
        in_degree = {node: len(self.edges_to.get(node, [])) for node in self.nodes}

        # Queue of nodes with no prerequisites
        queue = deque([node for node, degree in in_degree.items() if degree == 0])

        result = []  # List of parallel groups

        while queue:
            # All nodes in current queue can run in parallel
            current_group = []
            next_queue = deque()

            while queue:
                node = queue.popleft()
                current_group.append(node)

                # Reduce in-degree for all dependents
                for dependent in self.edges_from.get(node, []):
                    dep_type = self.dependency_types.get((node, dependent), DependencyType.DATA)

                    # Only count as blocking if it's a DATA or CONTROL dependency
                    if dep_type in (DependencyType.DATA, DependencyType.CONTROL):
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            next_queue.append(dependent)

            if current_group:
                result.append(current_group)

            queue = next_queue

        # Check for cycles
        if sum(len(group) for group in result) < len(self.nodes):
            cycles = self.detect_cycles()
            if cycles:
                raise ValueError(f"Circular dependency detected: {cycles}")

        return result

    def detect_cycles(self) -> list[list[str]]:
        """
        DFS-based cycle detection.
        Returns list of cycles (each cycle is a list of node IDs).
        """
        WHITE = 0  # Not visited
        GRAY = 1   # Currently being processed
        BLACK = 2  # Fully processed

        color = {node: WHITE for node in self.nodes}
        parent = {node: None for node in self.nodes}
        cycles = []

        def dfs(node: str, path: list[str]) -> bool:
            """Returns True if cycle found, appends cycle to path."""
            color[node] = GRAY
            path.append(node)

            for neighbor in self.edges_from.get(node, []):
                if color[neighbor] == GRAY:
                    # Found cycle - extract it
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True
                elif color[neighbor] == WHITE:
                    parent[neighbor] = node
                    if dfs(neighbor, path.copy()):
                        return True

            color[node] = BLACK
            return False

        for node in self.nodes:
            if color[node] == WHITE:
                dfs(node, [])

        return cycles

    def break_weakest_dependency(self, cycle: list[str]) -> bool:
        """
        Break a cycle by removing the weakest dependency.
        Returns True if cycle was broken.
        """
        # Find weakest dependency type in the cycle
        weakest_type = DependencyType.OPTIONAL
        weakest_pair = None

        for i in range(len(cycle) - 1):
            from_node = cycle[i]
            to_node = cycle[i + 1]
            dep_type = self.dependency_types.get((from_node, to_node))

            if dep_type and _dependency_strength(dep_type) < _dependency_strength(weakest_type):
                weakest_type = dep_type
                weakest_pair = (from_node, to_node)

        # Also check last to first
        if cycle:
            dep_type = self.dependency_types.get((cycle[-1], cycle[0]))
            if dep_type and _dependency_strength(dep_type) < _dependency_strength(weakest_type):
                weakest_type = dep_type
                weakest_pair = (cycle[-1], cycle[0])

        # Remove the weakest dependency
        if weakest_pair:
            from_node, to_node = weakest_pair
            if to_node in self.edges_from.get(from_node, []):
                self.edges_from[from_node].remove(to_node)
            if from_node in self.edges_to.get(to_node, []):
                self.edges_to[to_node].remove(from_node)
            del self.dependency_types[weakest_pair]
            return True

        return False

    def get_parallel_groups(self) -> list[list[str]]:
        """Get steps grouped for parallel execution."""
        return self.topological_sort()

    def get_critical_path(self) -> list[str]:
        """
        Get the critical path (longest sequence of blocking dependencies).
        """
        # Simple implementation: find longest path through DAG
        # More sophisticated implementations would use actual step durations
        sorted_groups = self.topological_sort()

        # The critical path goes through one node per group
        critical_path = []
        for group in sorted_groups:
            if group:
                critical_path.append(group[0])

        return critical_path

    def estimate_duration(self, step_durations: dict[str, float] | None = None) -> float:
        """
        Estimate total execution duration.
        If step_durations not provided, assume equal duration for all steps.
        """
        if not step_durations:
            # Assume 1 unit per step
            step_durations = {node: 1.0 for node in self.nodes}

        sorted_groups = self.topological_sort()
        total_duration = 0.0

        for group in sorted_groups:
            # Steps in a group run in parallel, so take max duration
            group_duration = max(
                (step_durations.get(node, 1.0) for node in group),
                default=0.0
            )
            total_duration += group_duration

        return total_duration

    def can_parallelize(self, step_a: str, step_b: str) -> bool:
        """Check if two steps can run in parallel."""
        # Check if there's a dependency path between them
        if self._has_path(step_a, step_b) or self._has_path(step_b, step_a):
            return False

        # Check for RESOURCE conflicts
        # (simplified - would need resource tracking for full implementation)
        return True

    def _has_path(self, from_node: str, to_node: str) -> bool:
        """Check if there's a path from from_node to to_node."""
        visited = set()
        queue = deque([from_node])

        while queue:
            current = queue.popleft()
            if current == to_node:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.edges_from.get(current, []))

        return False


def _dependency_strength(dep_type: DependencyType) -> int:
    """Get numeric strength of dependency type (lower = weaker)."""
    strengths = {
        DependencyType.OPTIONAL: 1,
        DependencyType.CONDITIONAL: 2,
        DependencyType.RESOURCE: 3,
        DependencyType.CONTROL: 4,
        DependencyType.DATA: 5,
    }
    return strengths.get(dep_type, 0)


def format_dependency_graph(graph: DependencyGraph) -> str:
    """Format dependency graph as human-readable string."""
    lines = []
    lines.append("Dependency Graph:")

    sorted_groups = graph.topological_sort()

    for i, group in enumerate(sorted_groups):
        lines.append(f"\nGroup {i + 1} (parallel):")
        for step_id in group:
            step = graph.nodes.get(step_id)
            if step:
                deps = graph.get_dependencies(step_id)
                deps_str = ", ".join(deps) if deps else "none"
                lines.append(f"  [{step_id}] {step.skill}:{step.action}")
                lines.append(f"    Dependencies: {deps_str}")

    critical_path = graph.get_critical_path()
    lines.append(f"\nCritical Path: {' -> '.join(critical_path)}")

    estimated = graph.estimate_duration()
    lines.append(f"Estimated Duration: {estimated} units")

    return "\n".join(lines)
