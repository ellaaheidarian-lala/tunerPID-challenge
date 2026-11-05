import ast
from fastapi import HTTPException

def check_source(source: bytes):
    """Screen common unsafe constructs; this does not sandbox Python."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, UnicodeError, RecursionError) as exc:
        raise HTTPException(400, 'File must contain valid Python source.') from exc
    blocked_calls = {'eval', 'exec', 'compile', 'open', '__import__', 'input', 'breakpoint', 'getattr', 'setattr', 'delattr', 'globals', 'locals', 'vars'}
    for node in ast.walk(tree):
        imports = [a.name.split('.')[0] for a in node.names] if isinstance(node, ast.Import) else ([node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
        if any(name not in {'numpy', 'math'} for name in imports) or (isinstance(node, ast.ImportFrom) and node.level):
            raise HTTPException(400, 'Only numpy and math imports are supported.')
        if isinstance(node, ast.Attribute) and node.attr.startswith('_'):
            raise HTTPException(400, 'Private and special attribute access is not supported.')
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in blocked_calls:
            raise HTTPException(400, f'Unsupported call: {node.func.id}')
    if not any(isinstance(n, ast.FunctionDef) and n.name == 'dynamics' for n in tree.body):
        raise HTTPException(400, 'Define a top-level dynamics(t, x, u) function.')
