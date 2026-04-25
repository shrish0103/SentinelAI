import re
from typing import List, Tuple

class CommandParser:
    """Robust parser to extract intent and arguments from user input."""
    
    @staticmethod
    def parse(raw_input: str) -> Tuple[str, List[str]]:
        # Normalize: strip, lowercase, remove leading slash
        clean = raw_input.strip().lower()
        if clean.startswith("/"):
            clean = clean[1:]
            
        # Split by whitespace, but keep it robust
        tokens = re.findall(r'"[^"]*"|\S+', clean)
        if not tokens:
            return "", []
            
        intent = tokens[0]
        args = [t.strip('"') for t in tokens[1:]]
        
        return intent, args
