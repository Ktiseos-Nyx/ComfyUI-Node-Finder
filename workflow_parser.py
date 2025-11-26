"""
ComfyUI Workflow Parser

Extracts and parses ComfyUI workflow metadata from PNG images,
building dictionaries for nodes, inputs/outputs, and connections.
"""

import json
from PIL import Image
from typing import Dict, Any, Tuple, Optional
import os


class WorkflowParser:
    """Parse ComfyUI workflow metadata from images."""
    
    def __init__(self, image_path: str):
        """
        Initialize the parser with an image path.
        
        Args:
            image_path: Path to the PNG image containing workflow metadata
        """
        self.image_path = image_path
        self.workflow_data = None
        self.nodes = {}
        self.io_map = {}
        self.connections = {}
    
    def load_workflow_from_image(self) -> Dict[str, Any]:
        """
        Load and extract workflow metadata from PNG image.
        
        Returns:
            Dictionary containing the workflow data
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If no workflow metadata found in image
        """
        if not os.path.exists(self.image_path):
            raise FileNotFoundError(f"Image file not found: {self.image_path}")
        
        try:
            image = Image.open(self.image_path)
        except Exception as e:
            raise ValueError(f"Failed to open image: {e}")
        
        # Extract metadata from PNG chunks
        workflow_str = None
        
        # Check for workflow in PNG info
        if hasattr(image, 'info'):
            # ComfyUI stores workflow in 'workflow' or 'prompt' keys
            if 'workflow' in image.info:
                workflow_str = image.info['workflow']
            elif 'prompt' in image.info:
                workflow_str = image.info['prompt']
        
        if not workflow_str:
            raise ValueError("No workflow metadata found in image")
        
        # Parse JSON
        try:
            self.workflow_data = json.loads(workflow_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse workflow JSON: {e}")
        
        return self.workflow_data
    
    def build_nodes_dictionary(self) -> Dict[str, Dict[str, Any]]:
        """
        Build dictionary of nodes with their core properties.
        
        Returns:
            Dictionary mapping node IDs to node properties
        """
        if not self.workflow_data:
            raise ValueError("No workflow data loaded. Call load_workflow_from_image() first.")
        
        self.nodes = {}
        
        # Handle different workflow formats
        nodes_data = self.workflow_data
        if isinstance(self.workflow_data, dict):
            # If workflow has a 'nodes' key, use that
            if 'nodes' in self.workflow_data:
                nodes_data = self.workflow_data['nodes']
            # If it's the prompt format, the keys are node IDs
            elif all(isinstance(k, str) and k.isdigit() for k in list(self.workflow_data.keys())[:5]):
                nodes_data = self.workflow_data
        
        # Parse nodes
        if isinstance(nodes_data, dict):
            for node_id, node_data in nodes_data.items():
                self.nodes[str(node_id)] = {
                    "class_type": node_data.get("class_type", "Unknown"),
                    "pos": node_data.get("pos", [0, 0]),
                    "size": node_data.get("size", [0, 0]),
                    "widgets_values": node_data.get("widgets_values", []),
                    "order": node_data.get("order", 0),
                    "mode": node_data.get("mode", 0)
                }
        elif isinstance(nodes_data, list):
            for node_data in nodes_data:
                node_id = str(node_data.get("id", ""))
                self.nodes[node_id] = {
                    "class_type": node_data.get("type", "Unknown"),
                    "pos": node_data.get("pos", [0, 0]),
                    "size": node_data.get("size", [0, 0]),
                    "widgets_values": node_data.get("widgets_values", []),
                    "order": node_data.get("order", 0),
                    "mode": node_data.get("mode", 0)
                }
        
        return self.nodes
    
    def build_io_dictionary(self) -> Dict[str, Dict[str, Any]]:
        """
        Build dictionary of node inputs and outputs.
        
        Returns:
            Dictionary mapping node IDs to their inputs/outputs
        """
        if not self.workflow_data:
            raise ValueError("No workflow data loaded. Call load_workflow_from_image() first.")
        
        self.io_map = {}
        
        # Handle different workflow formats
        nodes_data = self.workflow_data
        if isinstance(self.workflow_data, dict):
            if 'nodes' in self.workflow_data:
                nodes_data = self.workflow_data['nodes']
            elif all(isinstance(k, str) and k.isdigit() for k in list(self.workflow_data.keys())[:5]):
                nodes_data = self.workflow_data
        
        # Parse I/O for each node
        if isinstance(nodes_data, dict):
            for node_id, node_data in nodes_data.items():
                self._parse_node_io(str(node_id), node_data)
        elif isinstance(nodes_data, list):
            for node_data in nodes_data:
                node_id = str(node_data.get("id", ""))
                self._parse_node_io(node_id, node_data)
        
        return self.io_map
    
    def _parse_node_io(self, node_id: str, node_data: Dict[str, Any]):
        """Parse inputs and outputs for a single node."""
        self.io_map[node_id] = {
            "inputs": {},
            "outputs": {}
        }
        
        # Parse inputs
        if "inputs" in node_data:
            inputs = node_data["inputs"]
            if isinstance(inputs, dict):
                for input_name, input_data in inputs.items():
                    if isinstance(input_data, dict):
                        self.io_map[node_id]["inputs"][input_name] = {
                            "type": input_data.get("type", "unknown"),
                            "link": input_data.get("link", None)
                        }
                    elif isinstance(input_data, list) and len(input_data) >= 1:
                        # Format: [source_node_id, output_index]
                        self.io_map[node_id]["inputs"][input_name] = {
                            "type": "connection",
                            "link": input_data
                        }
                    else:
                        # Direct value
                        self.io_map[node_id]["inputs"][input_name] = {
                            "type": "value",
                            "value": input_data
                        }
            elif isinstance(inputs, list):
                for i, input_data in enumerate(inputs):
                    input_name = input_data.get("name", f"input_{i}")
                    self.io_map[node_id]["inputs"][input_name] = {
                        "type": input_data.get("type", "unknown"),
                        "link": input_data.get("link", None)
                    }
        
        # Parse outputs
        if "outputs" in node_data:
            outputs = node_data["outputs"]
            if isinstance(outputs, dict):
                for output_name, output_data in outputs.items():
                    self.io_map[node_id]["outputs"][output_name] = {
                        "type": output_data.get("type", "unknown"),
                        "links": output_data.get("links", [])
                    }
            elif isinstance(outputs, list):
                for i, output_data in enumerate(outputs):
                    output_name = output_data.get("name", f"output_{i}")
                    self.io_map[node_id]["outputs"][output_name] = {
                        "type": output_data.get("type", "unknown"),
                        "links": output_data.get("links", [])
                    }
    
    def build_connections_dictionary(self) -> Dict[str, Dict[str, Any]]:
        """
        Build dictionary of connections between nodes.
        
        Returns:
            Dictionary mapping link IDs to connection details
        """
        if not self.workflow_data:
            raise ValueError("No workflow data loaded. Call load_workflow_from_image() first.")
        
        self.connections = {}
        
        # Extract links from workflow
        if 'links' in self.workflow_data:
            links = self.workflow_data['links']
            if isinstance(links, list):
                for link in links:
                    if isinstance(link, list) and len(link) >= 6:
                        # Format: [link_id, source_node, source_slot, target_node, target_slot, type]
                        link_id = str(link[0])
                        self.connections[link_id] = {
                            "source_node": str(link[1]),
                            "source_output": link[2],
                            "target_node": str(link[3]),
                            "target_input": link[4],
                            "type": link[5] if len(link) > 5 else "unknown"
                        }
        
        # Also extract connections from node inputs
        nodes_data = self.workflow_data
        if isinstance(self.workflow_data, dict):
            if 'nodes' in self.workflow_data:
                nodes_data = self.workflow_data['nodes']
            elif all(isinstance(k, str) and k.isdigit() for k in list(self.workflow_data.keys())[:5]):
                nodes_data = self.workflow_data
        
        # Build connections from inputs
        if isinstance(nodes_data, dict):
            for target_node_id, node_data in nodes_data.items():
                self._extract_connections_from_node(str(target_node_id), node_data)
        elif isinstance(nodes_data, list):
            for node_data in nodes_data:
                target_node_id = str(node_data.get("id", ""))
                self._extract_connections_from_node(target_node_id, node_data)
        
        return self.connections
    
    def _extract_connections_from_node(self, target_node_id: str, node_data: Dict[str, Any]):
        """Extract connections from a node's input data."""
        if "inputs" not in node_data:
            return
        
        inputs = node_data["inputs"]
        if isinstance(inputs, dict):
            for input_name, input_data in inputs.items():
                if isinstance(input_data, list) and len(input_data) >= 2:
                    # Format: [source_node_id, source_output_index]
                    source_node_id = str(input_data[0])
                    source_output = input_data[1]
                    
                    # Create a connection ID
                    conn_id = f"{source_node_id}_{source_output}_to_{target_node_id}_{input_name}"
                    
                    if conn_id not in self.connections:
                        self.connections[conn_id] = {
                            "source_node": source_node_id,
                            "source_output": source_output,
                            "target_node": target_node_id,
                            "target_input": input_name,
                            "type": "inferred"
                        }
    
    def parse_all(self) -> Tuple[Dict, Dict, Dict]:
        """
        Parse workflow and build all three dictionaries.
        
        Returns:
            Tuple of (nodes, io_map, connections) dictionaries
        """
        self.load_workflow_from_image()
        self.build_nodes_dictionary()
        self.build_io_dictionary()
        self.build_connections_dictionary()
        
        return self.nodes, self.io_map, self.connections
    
    def save_to_file(self, output_path: str, format: str = "json", pretty: bool = True):
        """
        Save all dictionaries to a file for manual examination.
        
        Args:
            output_path: Path to save the output file
            format: Output format ('json' or 'txt')
            pretty: Whether to pretty-print the output (for JSON)
        """
        data = {
            "nodes": self.nodes,
            "io_map": self.io_map,
            "connections": self.connections,
            "metadata": {
                "source_image": self.image_path,
                "total_nodes": len(self.nodes),
                "total_connections": len(self.connections)
            }
        }
        
        if format.lower() == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)
        
        elif format.lower() == "txt":
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("COMFYUI WORKFLOW ANALYSIS\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Source Image: {self.image_path}\n")
                f.write(f"Total Nodes: {len(self.nodes)}\n")
                f.write(f"Total Connections: {len(self.connections)}\n\n")
                
                f.write("=" * 80 + "\n")
                f.write("NODES DICTIONARY\n")
                f.write("=" * 80 + "\n\n")
                for node_id, node_info in self.nodes.items():
                    f.write(f"Node ID: {node_id}\n")
                    for key, value in node_info.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("\n")
                
                f.write("=" * 80 + "\n")
                f.write("INPUTS/OUTPUTS DICTIONARY\n")
                f.write("=" * 80 + "\n\n")
                for node_id, io_info in self.io_map.items():
                    f.write(f"Node ID: {node_id}\n")
                    f.write("  Inputs:\n")
                    for input_name, input_info in io_info["inputs"].items():
                        f.write(f"    {input_name}: {input_info}\n")
                    f.write("  Outputs:\n")
                    for output_name, output_info in io_info["outputs"].items():
                        f.write(f"    {output_name}: {output_info}\n")
                    f.write("\n")
                
                f.write("=" * 80 + "\n")
                f.write("CONNECTIONS DICTIONARY\n")
                f.write("=" * 80 + "\n\n")
                for conn_id, conn_info in self.connections.items():
                    f.write(f"Connection ID: {conn_id}\n")
                    for key, value in conn_info.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("\n")
        
        print(f"Data saved to: {output_path}")


def main():
    """Example usage of the WorkflowParser."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python workflow_parser.py <image_path> [output_path]")
        print("Example: python workflow_parser.py workflow.png output.json")
        return
    
    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "workflow_analysis.json"
    
    try:
        # Create parser
        parser = WorkflowParser(image_path)
        
        # Parse workflow
        print(f"Loading workflow from: {image_path}")
        nodes, io_map, connections = parser.parse_all()
        
        # Print summary
        print(f"\nParsing complete!")
        print(f"  Nodes found: {len(nodes)}")
        print(f"  Connections found: {len(connections)}")
        
        # Save to file
        print(f"\nSaving analysis to: {output_path}")
        
        # Determine format from extension
        if output_path.endswith('.txt'):
            parser.save_to_file(output_path, format='txt')
        else:
            parser.save_to_file(output_path, format='json')
        
        print("\nDone!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
