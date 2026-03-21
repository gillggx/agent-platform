/**
 * DAG Validation Utilities
 * 
 * Core validation logic for DAG integrity, cycle detection, and type checking
 */

import { DAGNode, DAGEdge, ValidationResult, ValidationError, ValidationWarning } from '../types/dag';

/**
 * Detect cycles in the DAG using DFS
 * @returns Array of node IDs forming a cycle, empty if no cycle
 */
function detectCycle(nodes: DAGNode[], edges: DAGEdge[]): string[] {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const adjList = new Map<string, string[]>();

  // Build adjacency list
  for (const node of nodes) {
    adjList.set(node.id, []);
  }

  for (const edge of edges) {
    const neighbors = adjList.get(edge.source) || [];
    neighbors.push(edge.target);
    adjList.set(edge.source, neighbors);
  }

  // DFS to detect cycle
  const visited = new Set<string>();
  const recursionStack = new Set<string>();
  const cyclePath: string[] = [];

  function hasCycle(nodeId: string, path: string[]): boolean {
    visited.add(nodeId);
    recursionStack.add(nodeId);
    path.push(nodeId);

    const neighbors = adjList.get(nodeId) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (hasCycle(neighbor, [...path])) {
          return true;
        }
      } else if (recursionStack.has(neighbor)) {
        // Found cycle
        const cycleStart = path.indexOf(neighbor);
        cyclePath.push(...path.slice(cycleStart), neighbor);
        return true;
      }
    }

    recursionStack.delete(nodeId);
    return false;
  }

  for (const nodeId of nodeMap.keys()) {
    if (!visited.has(nodeId)) {
      if (hasCycle(nodeId, [])) {
        return cyclePath;
      }
    }
  }

  return [];
}

/**
 * Find isolated nodes (nodes with no incoming or outgoing edges)
 */
function findIsolatedNodes(nodes: DAGNode[], edges: DAGEdge[]): string[] {
  const connected = new Set<string>();

  for (const edge of edges) {
    connected.add(edge.source);
    connected.add(edge.target);
  }

  return nodes
    .map((n) => n.id)
    .filter((id) => !connected.has(id));
}

/**
 * Check if all required configurations are present
 */
function validateNodeConfigs(nodes: DAGNode[]): ValidationError[] {
  const errors: ValidationError[] = [];

  for (const node of nodes) {
    const { config } = node.data;

    if (!config.llm_model) {
      errors.push({
        type: 'missing_config',
        nodeId: node.id,
        message: `Node "${node.data.title}" is missing LLM model configuration`,
      });
    }

    if (config.temperature === undefined || config.temperature < 0 || config.temperature > 2) {
      errors.push({
        type: 'missing_config',
        nodeId: node.id,
        message: `Node "${node.data.title}" has invalid temperature (must be 0-2)`,
      });
    }

    if (!config.max_tokens || config.max_tokens < 100) {
      errors.push({
        type: 'missing_config',
        nodeId: node.id,
        message: `Node "${node.data.title}" has invalid max_tokens (minimum 100)`,
      });
    }
  }

  return errors;
}

/**
 * Check edge connectivity and type matching
 */
function validateEdgeConnectivity(
  nodes: DAGNode[],
  edges: DAGEdge[]
): ValidationError[] {
  const errors: ValidationError[] = [];
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  for (const edge of edges) {
    const source = nodeMap.get(edge.source);
    const target = nodeMap.get(edge.target);

    // Check if nodes exist
    if (!source) {
      errors.push({
        type: 'missing_edge',
        edgeId: edge.id,
        message: `Edge references non-existent source node "${edge.source}"`,
      });
    }

    if (!target) {
      errors.push({
        type: 'missing_edge',
        edgeId: edge.id,
        message: `Edge references non-existent target node "${edge.target}"`,
      });
    }

    // Check if output exists in source and input exists in target
    if (source) {
      const edgeLabel = edge.data?.label || '';
      if (edgeLabel && !source.data.outputs.includes(edgeLabel)) {
        errors.push({
          type: 'type_mismatch',
          edgeId: edge.id,
          message: `Source node "${source.data.title}" does not have output "${edgeLabel}"`,
        });
      }
    }

    if (target) {
      const edgeLabel = edge.data?.label || '';
      if (edgeLabel && !target.data.inputs.includes(edgeLabel)) {
        errors.push({
          type: 'type_mismatch',
          edgeId: edge.id,
          message: `Target node "${target.data.title}" does not have input "${edgeLabel}"`,
        });
      }
    }
  }

  return errors;
}

/**
 * Check for nodes without outputs (warning)
 */
function findNodesWithoutOutputs(nodes: DAGNode[], edges: DAGEdge[]): string[] {
  const hasOutgoing = new Set<string>();

  for (const edge of edges) {
    hasOutgoing.add(edge.source);
  }

  return nodes
    .map((n) => n.id)
    .filter((id) => !hasOutgoing.has(id));
}

/**
 * Main validation function
 */
export function validateDAG(nodes: DAGNode[], edges: DAGEdge[]): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];

  // Check for cycles
  const cycle = detectCycle(nodes, edges);
  if (cycle.length > 0) {
    errors.push({
      type: 'cycle',
      message: `Cycle detected in workflow: ${cycle.join(' → ')}`,
    });
  }

  // Check node configurations
  errors.push(...validateNodeConfigs(nodes));

  // Check edge connectivity
  errors.push(...validateEdgeConnectivity(nodes, edges));

  // Find isolated nodes (warning)
  const isolated = findIsolatedNodes(nodes, edges);
  for (const nodeId of isolated) {
    const node = nodes.find((n) => n.id === nodeId);
    warnings.push({
      type: 'isolated_node',
      nodeId,
      message: `Node "${node?.data.title}" is isolated (no connections)`,
    });
  }

  // Find nodes without outputs (warning)
  const noOutputs = findNodesWithoutOutputs(nodes, edges);
  for (const nodeId of noOutputs) {
    const node = nodes.find((n) => n.id === nodeId);
    if (!isolated.includes(nodeId)) {
      warnings.push({
        type: 'missing_output',
        nodeId,
        message: `Node "${node?.data.title}" has no outgoing connections`,
      });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Check if workflow can be executed
 */
export function isExecutable(nodes: DAGNode[], edges: DAGEdge[]): boolean {
  const validation = validateDAG(nodes, edges);
  return validation.valid && nodes.length > 0;
}

/**
 * Topological sort for execution order
 */
export function getExecutionOrder(nodes: DAGNode[], edges: DAGEdge[]): string[] {
  const adjList = new Map<string, string[]>();
  const inDegree = new Map<string, number>();

  // Initialize
  for (const node of nodes) {
    adjList.set(node.id, []);
    inDegree.set(node.id, 0);
  }

  // Build graph
  for (const edge of edges) {
    const neighbors = adjList.get(edge.source) || [];
    neighbors.push(edge.target);
    adjList.set(edge.source, neighbors);
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
  }

  // Kahn's algorithm
  const queue: string[] = [];
  for (const [nodeId, degree] of inDegree.entries()) {
    if (degree === 0) {
      queue.push(nodeId);
    }
  }

  const order: string[] = [];
  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    order.push(nodeId);

    const neighbors = adjList.get(nodeId) || [];
    for (const neighbor of neighbors) {
      const newDegree = (inDegree.get(neighbor) || 0) - 1;
      inDegree.set(neighbor, newDegree);
      if (newDegree === 0) {
        queue.push(neighbor);
      }
    }
  }

  return order;
}
