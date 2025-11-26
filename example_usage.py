"""
Example usage of the WorkflowParser class.

This demonstrates how to use the parser programmatically.
"""

import os
from workflow_parser import WorkflowParser


def get_image_path():
    """Prompt user for image path with validation."""
    while True:
        image_path = input("\nEnter the path to your ComfyUI workflow image (PNG): ").strip()
        
        # Remove quotes if user pasted a path with quotes
        image_path = image_path.strip('"').strip("'")
        
        if os.path.exists(image_path):
            if image_path.lower().endswith('.png'):
                return image_path
            else:
                print("Error: File must be a PNG image.")
        else:
            print(f"Error: File not found: {image_path}")
            retry = input("Try again? (y/n): ").strip().lower()
            if retry != 'y':
                return None


def get_output_path():
    """Prompt user for output path."""
    default_json = "workflow_analysis.json"
    default_txt = "workflow_analysis.txt"
    
    print("\nOutput options:")
    print("  1. JSON format (default: workflow_analysis.json)")
    print("  2. Text format (default: workflow_analysis.txt)")
    print("  3. Both formats")
    
    choice = input("Choose format (1/2/3) [1]: ").strip() or "1"
    
    if choice == "1":
        path = input(f"Output path [{default_json}]: ").strip() or default_json
        return [(path, "json")]
    elif choice == "2":
        path = input(f"Output path [{default_txt}]: ").strip() or default_txt
        return [(path, "txt")]
    elif choice == "3":
        json_path = input(f"JSON output path [{default_json}]: ").strip() or default_json
        txt_path = input(f"Text output path [{default_txt}]: ").strip() or default_txt
        return [(json_path, "json"), (txt_path, "txt")]
    else:
        print("Invalid choice, using JSON format.")
        return [(default_json, "json")]


def example_basic_usage():
    """Basic example: parse and save to JSON."""
    # Prompt for image path
    image_path = get_image_path()
    if not image_path:
        print("Cancelled.")
        return
    
    # Initialize parser
    parser = WorkflowParser(image_path)
    
    # Parse all data
    print("\nParsing workflow...")
    nodes, io_map, connections = parser.parse_all()
    
    # Prompt for output path
    outputs = get_output_path()
    
    # Save to file(s)
    for output_path, format_type in outputs:
        parser.save_to_file(output_path, format=format_type)
    
    # Print summary
    print(f"\n✓ Found {len(nodes)} nodes")
    print(f"✓ Found {len(connections)} connections")


def example_detailed_usage():
    """Detailed example: parse step by step and examine data."""
    # Prompt for image path
    image_path = get_image_path()
    if not image_path:
        print("Cancelled.")
        return
    
    parser = WorkflowParser(image_path)
    
    # Step 1: Load workflow from image
    print("\nLoading workflow from image...")
    workflow_data = parser.load_workflow_from_image()
    print("✓ Workflow loaded successfully")
    
    # Step 2: Build nodes dictionary
    print("\nBuilding nodes dictionary...")
    nodes = parser.build_nodes_dictionary()
    print(f"✓ Nodes ({len(nodes)}):")
    for node_id, node_info in list(nodes.items())[:3]:  # Show first 3
        print(f"  {node_id}: {node_info['class_type']}")
    if len(nodes) > 3:
        print(f"  ... and {len(nodes) - 3} more")
    
    # Step 3: Build I/O dictionary
    print("\nBuilding I/O dictionary...")
    io_map = parser.build_io_dictionary()
    print(f"✓ I/O Map created for {len(io_map)} nodes")
    
    # Step 4: Build connections dictionary
    print("\nBuilding connections dictionary...")
    connections = parser.build_connections_dictionary()
    print(f"✓ Connections ({len(connections)}):")
    for conn_id, conn_info in list(connections.items())[:3]:  # Show first 3
        print(f"  {conn_info['source_node']} -> {conn_info['target_node']}")
    if len(connections) > 3:
        print(f"  ... and {len(connections) - 3} more")
    
    # Prompt for output
    outputs = get_output_path()
    
    # Save to file(s)
    for output_path, format_type in outputs:
        parser.save_to_file(output_path, format=format_type)


def example_query_nodes():
    """Example: query specific node types."""
    # Prompt for image path
    image_path = get_image_path()
    if not image_path:
        print("Cancelled.")
        return
    
    parser = WorkflowParser(image_path)
    print("\nParsing workflow...")
    nodes, io_map, connections = parser.parse_all()
    
    # Show all unique node types
    node_types = set(node_info['class_type'] for node_info in nodes.values())
    print(f"\n✓ Found {len(node_types)} unique node types:")
    for node_type in sorted(node_types):
        count = sum(1 for n in nodes.values() if n['class_type'] == node_type)
        print(f"  - {node_type}: {count}")
    
    # Prompt for node type to search
    search_type = input("\nEnter node type to search for (or press Enter to skip): ").strip()
    if search_type:
        matching_nodes = {
            node_id: node_info 
            for node_id, node_info in nodes.items() 
            if node_info['class_type'] == search_type
        }
        print(f"\nFound {len(matching_nodes)} '{search_type}' nodes")
        print(f"\nIDs: {matching_nodes.keys()}")
    
    # Prompt for node ID to examine connections
    node_id = input("\nEnter node ID to examine connections (or press Enter to skip): ").strip()
    if node_id and node_id in nodes:
        incoming = [
            conn for conn in connections.values() 
            if conn['target_node'] == node_id
        ]
        outgoing = [
            conn for conn in connections.values() 
            if conn['source_node'] == node_id
        ]
        
        print(f"\nNode {node_id} ({nodes[node_id]['class_type']}):")
        print(f"  Incoming connections:")
        for conn in incoming:
            # For incoming: we want the OUTPUT name from the SOURCE node
            output_names = list(io_map[conn['source_node']]['outputs'].keys())
            output_name = output_names[conn['source_output']] if conn['source_output'] < len(output_names) else 'Unknown'
            
            # And the INPUT name on the TARGET node (current node)
            input_names = list(io_map[node_id]['inputs'].keys())
            input_name = input_names[conn['target_input']] if conn['target_input'] < len(input_names) else 'Unknown'
            
            print(f"    Source:{conn['source_node']} Output:{output_name} Node Type:{nodes[conn['source_node']]['class_type']} -> Input:{input_name} Type:{conn['type']}")

        print("\nOutgoing connections:")
        for conn in outgoing:
            # For outgoing: we want the OUTPUT name from the SOURCE node (current node)
            output_names = list(io_map[node_id]['outputs'].keys())
            output_name = output_names[conn['source_output']] if conn['source_output'] < len(output_names) else 'Unknown'
            
            # And the INPUT name on the TARGET node
            input_names = list(io_map[conn['target_node']]['inputs'].keys())
            input_name = input_names[conn['target_input']] if conn['target_input'] < len(input_names) else 'Unknown'
            
            print(f"    Target:{conn['target_node']} Output:{output_name} Node Type:{nodes[conn['target_node']]['class_type']} -> Input:{input_name} Type:{conn['type']}")

        print("\nWidget Values:")
        for widget in nodes[node_id]['widgets_values']:
            print(f"  {widget}")
    elif node_id:
        print(f"Node ID '{node_id}' not found")


if __name__ == "__main__":
    print("ComfyUI Workflow Parser - Interactive Examples")
    print("=" * 50)
    print("\nChoose an example:")
    print("  1. Basic usage (parse and save)")
    print("  2. Detailed usage (step-by-step parsing)")
    print("  3. Query nodes (search and examine)")
    
    choice = input("\nEnter choice (1/2/3) [1]: ").strip() or "1"
    
    if choice == "1":
        example_basic_usage()
    elif choice == "2":
        example_detailed_usage()
    elif choice == "3":
        example_query_nodes()
    else:
        print("Invalid choice. Running basic example.")
        example_basic_usage()
