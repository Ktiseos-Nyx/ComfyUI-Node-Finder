# ComfyUI-Node-Finder
Search a git url for CUI nodes

## Workflow Parser

Parse ComfyUI workflow metadata from PNG images and extract structured data about nodes, inputs/outputs, and connections.

### Installation

```bash
pip install -r requirements.txt
```

### Usage

#### Command Line

```bash
# Parse workflow and save to JSON
python workflow_parser.py workflow_image.png output.json

# Parse workflow and save to text file
python workflow_parser.py workflow_image.png output.txt
```

#### Programmatic Usage

```python
from workflow_parser import WorkflowParser

# Initialize parser
parser = WorkflowParser("path/to/workflow_image.png")

# Parse all data at once
nodes, io_map, connections = parser.parse_all()

# Save to file
parser.save_to_file("analysis.json", format="json")  # JSON format
parser.save_to_file("analysis.txt", format="txt")    # Text format

# Access individual dictionaries
print(f"Nodes: {len(nodes)}")
print(f"Connections: {len(connections)}")
```

### Output Structure

The parser generates three dictionaries:

1. **Nodes Dictionary**: Core node properties (type, position, size, widgets)
2. **I/O Map Dictionary**: Input and output definitions for each node
3. **Connections Dictionary**: How nodes are connected to each other

See `example_usage.py` for more detailed examples.
