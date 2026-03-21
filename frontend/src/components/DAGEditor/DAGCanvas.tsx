/**
 * DAG Canvas Component
 * 
 * React Flow-based canvas for visualizing and editing DAG workflows.
 * Supports node dragging, connection creation, and visual validation feedback.
 */

import React, { useCallback, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Connection,
  addEdge,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  MiniMap,
  SelectionMode,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useDagStore } from '@/store/dagStore';
import { DAGNode as DAGNodeType, DAGEdge as DAGEdgeType } from '@/types/dag';
import AgentNode from './AgentNode';
import './styles/dag-canvas.css';

interface DAGCanvasProps {
  onNodeSelect?: (nodeId: string | null) => void;
  onEdgeSelect?: (edgeId: string | null) => void;
}

/**
 * Transform DAG nodes and edges from Zustand store to React Flow format
 */
const transformToReactFlow = (
  dagNodes: DAGNodeType[],
  dagEdges: DAGEdgeType[]
): { nodes: Node[]; edges: Edge[] } => {
  const nodes: Node[] = dagNodes.map((node) => ({
    id: node.id,
    data: {
      label: node.data.title,
      role: node.role,
      config: node.data.config,
      inputs: node.data.inputs,
      outputs: node.data.outputs,
      color: node.data.color,
    },
    position: { x: node.position.x, y: node.position.y },
    type: 'agentNode',
  }));

  const edges: Edge[] = dagEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.data?.label || '',
    data: edge.data,
    style: edge.style as any,
  }));

  return { nodes, edges };
};

export const DAGCanvas: React.FC<DAGCanvasProps> = ({
  onNodeSelect,
  onEdgeSelect,
}) => {
  const { workflow, validation, updateNode, addEdge: storeAddEdge } =
    useDagStore();

  const initialNodes = useMemo(() => {
    if (!workflow) return [];
    return transformToReactFlow(workflow.nodes, workflow.edges).nodes;
  }, [workflow?.nodes]);

  const initialEdges = useMemo(() => {
    if (!workflow) return [];
    return transformToReactFlow(workflow.nodes, workflow.edges).edges;
  }, [workflow?.edges]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync React Flow nodes/edges with Zustand store
  const handleNodesChange = useCallback(
    (changes: any[]) => {
      onNodesChange(changes);

      // Update positions in store when nodes are dragged
      changes.forEach((change: any) => {
        if (change.type === 'position' && change.positionAbsolute && workflow) {
          const dagNode = workflow.nodes.find((n) => n.id === change.id);
          if (dagNode) {
            updateNode({
              ...dagNode,
              position: {
                x: change.positionAbsolute.x,
                y: change.positionAbsolute.y,
              },
            });
          }
        }

        if (change.type === 'select') {
          if (change.selected) {
            onNodeSelect?.(change.id);
          } else {
            onNodeSelect?.(null);
          }
        }
      });
    },
    [workflow, updateNode, onNodesChange, onNodeSelect]
  );

  // Handle new connections
  const handleConnect = useCallback(
    (connection: Connection) => {
      const newEdge: DAGEdgeType = {
        id: `edge-${connection.source}-${connection.target}-${Date.now()}`,
        source: connection.source || '',
        target: connection.target || '',
        data: {
          label: '',
          type: 'data',
        },
      };

      storeAddEdge(newEdge);
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            id: newEdge.id,
          } as any,
          eds
        )
      );
    },
    [storeAddEdge, setEdges]
  );

  // Handle edge click (select)
  const handleEdgeClick = useCallback(
    (event: React.MouseEvent, edge: Edge) => {
      event.preventDefault();
      onEdgeSelect?.(edge.id);
    },
    [onEdgeSelect]
  );

  // Get color based on validation status
  const getNodeColor = (nodeId: string) => {
    const nodeErrors = validation.errors.filter((e) => e.nodeId === nodeId);
    if (nodeErrors.length > 0) return '#ff4d4f'; // red
    const nodeWarnings = validation.warnings.filter((w) => w.nodeId === nodeId);
    if (nodeWarnings.length > 0) return '#faad14'; // orange
    return '#1890ff'; // blue (default)
  };

  // Update node styles based on validation
  const styledNodes = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        style: {
          ...node.style,
          borderColor: getNodeColor(node.id),
          borderWidth: 2,
        },
      })),
    [nodes, validation]
  );

  const nodeTypes = useMemo(
    () => ({
      agentNode: AgentNode as any,
    }),
    []
  );

  return (
    <div className="dag-canvas-container" style={{ width: '100%', height: '600px' }}>
      <ReactFlow
        nodes={styledNodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={handleConnect}
        onEdgeClick={handleEdgeClick}
        nodeTypes={nodeTypes}
        fitView
        selectionMode={SelectionMode.Partial}
        deleteKeyCode="Delete"
      >
        <Background color="#aaa" gap={16} />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
};

export default DAGCanvas;
