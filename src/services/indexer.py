"""
Code indexer using Tree-Sitter for parsing Python code.

Provides repo mapping and code structure analysis.
"""

import os
from tree_sitter import Language, Parser
import tree_sitter_python
from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class CodeIndexer:
    """Tree-Sitter based code indexer for Python files."""
    
    def __init__(self):
        """Initialize the code indexer with Python language support."""
        logger.info("Initializing CodeIndexer")
        
        # Load the Python language
        try:
            # Try modern tree-sitter-python API
            self.PY_LANGUAGE = Language(tree_sitter_python.language())
            logger.debug("Loaded tree-sitter-python using modern API")
        except TypeError:
            # Fallback for older versions
            try:
                self.PY_LANGUAGE = Language(tree_sitter_python.language(), "python")
                logger.debug("Loaded tree-sitter-python using legacy API")
            except Exception as e:
                logger.error(f"Failed to load tree-sitter-python: {e}", exc_info=True)
                raise
            
        self.parser = Parser()
        self.parser.set_language(self.PY_LANGUAGE)
        logger.info("CodeIndexer initialized successfully")

    def _get_definitions(self, code: str) -> str:
        """
        Extract class and function definitions from code.
        
        Args:
            code: Python source code
            
        Returns:
            String containing signatures of all definitions
        """
        try:
            tree = self.parser.parse(bytes(code, "utf8"))
        except Exception as e:
            logger.error(f"Failed to parse code: {e}")
            return f"Error parsing code: {str(e)}"
        
        # Query for class and function definitions
        query_scm = """
        (class_definition
            name: (identifier) @name) @class
        (function_definition
            name: (identifier) @name) @function
        """
        
        try:
            query = self.PY_LANGUAGE.query(query_scm)
            captures = query.captures(tree.root_node)
        except Exception as e:
            logger.error(f"Failed to query tree: {e}")
            return f"Error querying code: {str(e)}"
        
        definitions = []
        for node, tag in captures:
            if tag == "name":
                parent = node.parent
                if parent:
                    # Get the first line of the definition
                    start_byte = parent.start_byte
                    end_byte = code.find('\n', start_byte)
                    if end_byte == -1:
                        end_byte = len(code)
                    
                    line = code[start_byte:end_byte].strip()
                    if line.endswith(":"):
                        definitions.append(line)
                    else:
                        definitions.append(line + "...")
        
        return "\n".join(definitions)

    def build_repo_map(self, root_path: str) -> str:
        """
        Build a map of all Python files in the repo with their definitions.
        
        Args:
            root_path: Root directory to scan
            
        Returns:
            String containing repo structure with definitions
        """
        logger.info(f"Building repo map for: {root_path}")
        
        if not os.path.exists(root_path):
            error_msg = f"Path does not exist: {root_path}"
            logger.error(error_msg)
            return error_msg
        
        repo_map = []
        max_file_size = settings.indexer_max_file_size_mb * 1024 * 1024  # Convert to bytes
        file_count = 0
        error_count = 0
        
        for root, _, files in os.walk(root_path):
            for file in files:
                # Check if file extension is allowed
                if not any(file.endswith(ext) for ext in settings.indexer_file_extensions):
                    continue
                
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_path)
                
                try:
                    # Check file size
                    file_size = os.path.getsize(full_path)
                    if file_size > max_file_size:
                        logger.warning(f"Skipping large file ({file_size} bytes): {rel_path}")
                        repo_map.append(f"File: {rel_path}\n[File too large to index]\n")
                        continue
                    
                    # Read and parse file
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    defs = self._get_definitions(content)
                    if defs:
                        repo_map.append(f"File: {rel_path}\n{defs}\n")
                        file_count += 1
                    
                except UnicodeDecodeError as e:
                    logger.warning(f"Unicode error in file {rel_path}: {e}")
                    repo_map.append(f"File: {rel_path}\nError: Unable to decode file\n")
                    error_count += 1
                    
                except PermissionError as e:
                    logger.warning(f"Permission denied for file {rel_path}: {e}")
                    repo_map.append(f"File: {rel_path}\nError: Permission denied\n")
                    error_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing file {rel_path}: {e}")
                    repo_map.append(f"File: {rel_path}\nError: {str(e)}\n")
                    error_count += 1
        
        logger.info(f"Repo map complete: {file_count} files indexed, {error_count} errors")
        return "\n".join(repo_map)
