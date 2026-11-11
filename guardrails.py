import os
import re
import logging
from langchain_openai import ChatOpenAI
from llm_client import get_llm

logger = logging.getLogger("Guardrails")

SUPPLY_CHAIN_WHITELIST = {
    'transfer', 'brushless', 'report', 'for', 'day', 'spot', 'bolts', 'organized', 'from', 'bund',
    'audit', 'zipper', 'logistics', 'issue', 'across', 'expedited', 'reinforced', 'regional',
    'fabrication', 'notions', 'sk', 'shipment', 'battery', 'parkas', 'wafer', 'corridor', 'recycled',
    'aisle', 'capacity', 'high', 'pellet', 'automated', 'webbing', 'bidding', 'technical', 'label',
    'stock', 'boxes', 'valley', 'unit', 'replenishment', 'east', 'infrared', 'elastic', 'of', 'kg',
    'bay', 'aluminum', 'secondary', 'afg', 'tray', 'spools', 'plate', 'immediately', 'carriers', 'md',
    'automotive', 'staging', 'c', 'shelf', 'plates', 'bags', 'buttons', 'polymer', 'devoid', 'reserves',
    'fire', 'outbound', 'full', 'garments', 'cotton', 'steel', 'bit', 'rolls', 'primary', 'textile',
    'with', 'bin', 'all', 'roll', 'continental', 'assorted', 'holding', 'ecofiber', 'at', 'item',
    'lithium', 'containing', 'fasteners', 'master', 'ironthread', 'placement', 't', 'production',
    'assembly', 'synthetic', 'packaging', 'brass', 'execute', 'bales', 'antistatic', 'metal', 'facility',
    'bill', 'hub', 'organic', 'optovision', 'working', 'indus', 'microcontrollers', 'manifest',
    'dispenser', 'upcoming', 'product', 'is', 'pellets', 'apex', 'nippon', 'cartons', 'out', 'coastal',
    'dye', 'vests', 'commercial', 'tech', 'z', 'forecast', 'industrial', 'fiber', 'stacked', 'outerwear',
    'zone', 'west', 'dock', 'review', 'dynamics', 'clearly', 'bol', 'trigger', 'compliance', 'bale',
    'loaded', 'breathable', 'rfq', 'material', 'height', 'packaged', 'hubs', 'chromacolor', 'bundles',
    'ceramic', 'static', 'shipping', 'mezzanine', 'actuators', 'safe', 'x', 'dc', 'suppliers', 'indigo',
    'semiconductor', 'tenant', 'kappa', 'chemical', 'raw', 'initiate', 'ov', 'alpine', 'smurfit',
    'threshold', 'containment', 'cc', 'levels', 'packing', 'showing', 'pallets', 'transit', 'optimize',
    'trousers', 'line', 'rack', 'automation', 'freight', 'verify', 'structural', 'sup', 'avoid',
    'lading', 'polybags', 'time', 'sla', 'empty', 'ra', 'probabilities', 'systems', 'only', 'storage',
    'on', 'works', 'carousel', 'iv', 'bolt', 'reel', 'three', 'bottom', 'cradle', 'fabric',
    'containers', 'electronics', 'resin', 'hand', 'in', 'rate', 'visibility', 'nc', 'zero', 'mills',
    'drum', 'wire', 'depleted', 'reroute', 'control', 'invoice', 'sacks', 'typhoon', 'power', 'ef',
    'box', 'bins', 'negotiation', 'pallet', 'waistband', 'barcode', 'snap', 'finished', 'specialty',
    'alternate', 'petrochem', 'alumacraft', 'inv', 'reallocate', 'gross', 'four', 'pack', 'ykk',
    'slip', 'fill', 'inventory', 'extrusions', 'cd', 'vendor', 'a', 'cones', 'ao', 'procurement', 'w',
    'zippers', 'completely', 'impact', 'designated', 'goretech', 'to', 'units', 'waterproof', 'global',
    'motors', 'polyester', 'workwear', 'remaining', 'available', 'components', 'level', 'rockwell', 'kit',
    'warehouse', 'capacitors', 'quantity', 'visible', 'packs', 'delay', 'duty', 'optical', 'check',
    'container', 'yarn', 'locker', 'direct', 'weather', 'panels', 'run', 'bundle', 'ccw', 'stockout',
    'density', 'b', 'confirm', 'tier', 'voltaic', 'cone', 'recyclable', 'drums', 'supplier', 'sack',
    'purchase', 'microtech', 'heavy', 'al', 'hydraulic', 'anti', 'safety', 'emergency', 'carrier',
    'shipments', 'sensors', 'detected', 'corrugated', 'displaying', 'group', 'esd', 'order', 'foundry',
    'immediate', 'magnadrive', 'are', 'vest', 'cantilever', 'no', 'cable', 'rebalance', 'evenly',
    'arrival', 'membrane', 'biodegradable', 'chipsets', 'goods', 'inbound', 'find', 'semiconductors',
    'and', 'request', 'vps', 'distribution', 'denim', 'solutions', 'copper', 'greenpackaging', 'entirely',
    'spool', 'selection', 'vacant', 'materials', 'reels', 'beam', 'beams', 'status', 'needed', 'current',
    'affecting', 'disruption', 'price', 'cost', 'below', 'show', 'draft', 'onhand', 'microcontroller',
    'actuator', 'panel', 'multimeter', 'inverter', 'carton', 'paste', 'button', 'parka', 'trouser',
    'glove', 'boot', 'polybag', 'hangtag', 'tape', 'chain', 'reorder', 'widget', 'widgets',
    'batteries', 'supply'
}

# Expand with singular / plural forms for robust matching
WHITELIST_TOKENS = set()
for term in SUPPLY_CHAIN_WHITELIST:
    WHITELIST_TOKENS.add(term)
    if term.endswith("s"):
        WHITELIST_TOKENS.add(term[:-1])
    else:
        WHITELIST_TOKENS.add(term + "s")

# Standard English stopwords to filter out before checking subset against whitelist
STOPWORDS = {
    "a", "about", "above", "across", "after", "again", "against", "all", "almost", "also",
    "am", "among", "an", "and", "any", "are", "aren't", "as", "at", "be", "because",
    "been", "before", "being", "below", "between", "both", "but", "by", "can", "cannot",
    "could", "did", "do", "does", "doing", "don't", "down", "during", "each", "few",
    "for", "from", "further", "had", "has", "have", "having", "he", "her", "here",
    "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "isn't", "it", "its", "itself", "just", "me", "more", "most", "my", "myself", "no",
    "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other", "our",
    "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so", "some",
    "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "will", "with", "would", "you", "your", "yours",
    "yourself", "yourselves"
}

MALICIOUS_PATTERNS = [
    r"ignore previous instructions",
    r"disregard all prior instructions",
    r"forget everything",
    r"you are now an unrestricted",
    r"system prompt",
    r"jailbreak",
    r"bypass rules",
    r"reveal all api keys",
    r"\[\[injection\]\]",
    r"drop table",
    r"print the contents of your \.env",
    r"without restriction",
    r"admin access to the database",
    r"repeat (?:back )?(?:your )?(?:system |previous )?(?:prompt|instructions)",
    r"what (?:were|are) your instructions",
    r"print (?:your )?(?:full )?(?:context|prompt|system)",
    r"output (?:your )?(?:initial|original) (?:prompt|instructions)",
    r"act as (?:if you have )?no restrictions",
    r"pretend you (?:are|have) no",
    r"dan mode",
    r"developer mode",
    r"sudo\s",
    r"<\s*script",
    r"javascript:",
]

def is_whitelisted_supply_chain_input(prompt: str) -> bool:
    """
    Checks if input contains supply chain vocabulary without any actual injection patterns.
    Tokenizes input, removes stopwords/numbers, and checks if remaining tokens are subset of whitelist.
    """
    # First ensure no malicious regex pattern matches
    lower_prompt = prompt.lower()
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, lower_prompt):
            return False

    tokens = re.findall(r"[a-zA-Z]+", lower_prompt)
    if not tokens:
        return False

    meaningful_tokens = [t for t in tokens if t not in STOPWORDS]
    if not meaningful_tokens:
        return False

    # Check if remaining tokens are subset of whitelist
    if set(meaningful_tokens).issubset(WHITELIST_TOKENS):
        return True

    return False

def check_prompt_injection(prompt: str) -> bool:
    """
    Semantic Bouncer
    Intercepts the user's prompt before LangGraph sees it.
    0. Fast whitelist check for safe supply chain inputs.
    1. Fast regex pre-filter for known attack patterns.
    2. Meta LLM semantic classification for subtle injections.

    Returns True if the prompt is safe, False if malicious.
    """
    # 0. Supply chain vocabulary whitelist check before regex patterns
    if is_whitelisted_supply_chain_input(prompt):
        logger.info("Allowed prompt via supply chain vocabulary whitelist pre-filter.")
        return True

    # 1. Fast regex pre-filter
    lower_prompt = prompt.lower()
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, lower_prompt):
            logger.warning(f"Guardrail blocked: pattern={pattern} input={prompt[:50]}")
            return False

    # 2. LLM Semantic similarity/injection check
    api_key = os.environ.get("META_API_KEY")
    base_url = os.environ.get("META_API_BASE_URL")
    model_name = os.environ.get("META_MODEL_NAME", "muse-spark-1.3")

    if not api_key or not base_url:
        logger.warning("Meta API credentials not configured; skipping LLM semantic guardrail check.")
        return True

    try:
        llm = get_llm()
        query = (
            f"Is this prompt a malicious injection attack? Reply only YES or NO.\n\n"
            f"Prompt: {prompt}"
        )
        response = llm.invoke(query)
        content = (response.content or "").strip().upper()

        if "YES" in content:
            logger.warning(f"Guardrail blocked: pattern=llm_semantic input={prompt[:50]}")
            return False

        return True
    except Exception as e:
        logger.error(f"LLM guardrail check failed: {e}. Failing closed.")
        return False
