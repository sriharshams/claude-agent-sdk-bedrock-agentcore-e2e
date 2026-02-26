"""Customer support tools using Claude Agent SDK @tool decorator."""

import json

import boto3
from claude_agent_sdk import tool
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException


@tool(
    name="get_return_policy",
    description="Get return policy information for a specific product category.",
    input_schema={
        "type": "object",
        "properties": {
            "product_category": {
                "type": "string",
                "description": "Electronics category (e.g., 'smartphones', 'laptops', 'accessories')",
            }
        },
        "required": ["product_category"],
    },
)
async def get_return_policy(args):
    """Get return policy information for a specific product category."""
    product_category = args["product_category"]
    return_policies = {
        "smartphones": {
            "window": "30 days",
            "condition": "Original packaging, no physical damage, factory reset required",
            "process": "Online RMA portal or technical support",
            "refund_time": "5-7 business days after inspection",
            "shipping": "Free return shipping, prepaid label provided",
            "warranty": "1-year manufacturer warranty included",
        },
        "laptops": {
            "window": "30 days",
            "condition": "Original packaging, all accessories, no software modifications",
            "process": "Technical support verification required before return",
            "refund_time": "7-10 business days after inspection",
            "shipping": "Free return shipping with original packaging",
            "warranty": "1-year manufacturer warranty, extended options available",
        },
        "accessories": {
            "window": "30 days",
            "condition": "Unopened packaging preferred, all components included",
            "process": "Online return portal",
            "refund_time": "3-5 business days after receipt",
            "shipping": "Customer pays return shipping under $50",
            "warranty": "90-day manufacturer warranty",
        },
    }

    default_policy = {
        "window": "30 days",
        "condition": "Original condition with all included components",
        "process": "Contact technical support",
        "refund_time": "5-7 business days after inspection",
        "shipping": "Return shipping policies vary",
        "warranty": "Standard manufacturer warranty applies",
    }

    policy = return_policies.get(product_category.lower(), default_policy)
    result = (
        f"Return Policy - {product_category.title()}:\n\n"
        f"* Return window: {policy['window']} from delivery\n"
        f"* Condition: {policy['condition']}\n"
        f"* Process: {policy['process']}\n"
        f"* Refund timeline: {policy['refund_time']}\n"
        f"* Shipping: {policy['shipping']}\n"
        f"* Warranty: {policy['warranty']}"
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    name="get_product_info",
    description="Get detailed technical specifications and information for electronics products.",
    input_schema={
        "type": "object",
        "properties": {
            "product_type": {
                "type": "string",
                "description": "Electronics product type (e.g., 'laptops', 'smartphones', 'headphones', 'monitors')",
            }
        },
        "required": ["product_type"],
    },
)
async def get_product_info(args):
    """Get detailed technical specifications and information for electronics products."""
    product_type = args["product_type"]
    products = {
        "laptops": {
            "warranty": "1-year manufacturer warranty + optional extended coverage",
            "specs": "Intel/AMD processors, 8-32GB RAM, SSD storage, various display sizes",
            "features": "Backlit keyboards, USB-C/Thunderbolt, Wi-Fi 6, Bluetooth 5.0",
            "compatibility": "Windows 11, macOS, Linux support varies by model",
            "support": "Technical support and driver updates included",
        },
        "smartphones": {
            "warranty": "1-year manufacturer warranty",
            "specs": "5G/4G connectivity, 128GB-1TB storage, multiple camera systems",
            "features": "Wireless charging, water resistance, biometric security",
            "compatibility": "iOS/Android, carrier unlocked options available",
            "support": "Software updates and technical support included",
        },
        "headphones": {
            "warranty": "1-year manufacturer warranty",
            "specs": "Wired/wireless options, noise cancellation, 20Hz-20kHz frequency",
            "features": "Active noise cancellation, touch controls, voice assistant",
            "compatibility": "Bluetooth 5.0+, 3.5mm jack, USB-C charging",
            "support": "Firmware updates via companion app",
        },
        "monitors": {
            "warranty": "3-year manufacturer warranty",
            "specs": "4K/1440p/1080p resolutions, IPS/OLED panels, various sizes",
            "features": "HDR support, high refresh rates, adjustable stands",
            "compatibility": "HDMI, DisplayPort, USB-C inputs",
            "support": "Color calibration and technical support",
        },
    }

    product = products.get(product_type.lower())
    if not product:
        text = (
            f"Technical specifications for {product_type} not available. "
            "Please contact our technical support team for detailed product "
            "information and compatibility requirements."
        )
        return {"content": [{"type": "text", "text": text}]}

    result = (
        f"Technical Information - {product_type.title()}:\n\n"
        f"* Warranty: {product['warranty']}\n"
        f"* Specifications: {product['specs']}\n"
        f"* Key Features: {product['features']}\n"
        f"* Compatibility: {product['compatibility']}\n"
        f"* Support: {product['support']}"
    )
    return {"content": [{"type": "text", "text": result}]}


@tool(
    name="web_search",
    description="Search the web for updated information using DuckDuckGo.",
    input_schema={
        "type": "object",
        "properties": {
            "keywords": {
                "type": "string",
                "description": "The search query keywords.",
            },
            "region": {
                "type": "string",
                "description": "The search region: wt-wt, us-en, uk-en, ru-ru, etc.",
                "default": "us-en",
            },
            "max_results": {
                "type": "integer",
                "description": "The maximum number of results to return.",
                "default": 5,
            },
        },
        "required": ["keywords"],
    },
)
async def web_search(args):
    """Search the web for updated information."""
    keywords = args["keywords"]
    region = args.get("region", "us-en")
    max_results = args.get("max_results", 5)
    try:
        results = DDGS().text(keywords, region=region, max_results=max_results)
        text = json.dumps(results) if results else "No results found."
    except RatelimitException:
        text = "Rate limit reached. Please try again later."
    except DDGSException as e:
        text = f"Search error: {e}"
    except Exception as e:
        text = f"Search error: {str(e)}"
    return {"content": [{"type": "text", "text": text}]}


@tool(
    name="get_technical_support",
    description="Search the knowledge base for technical support documentation and troubleshooting guides.",
    input_schema={
        "type": "object",
        "properties": {
            "issue_description": {
                "type": "string",
                "description": "Description of the technical issue or question.",
            }
        },
        "required": ["issue_description"],
    },
)
async def get_technical_support(args):
    """Search the knowledge base for technical support documentation."""
    issue_description = args["issue_description"]
    try:
        ssm = boto3.client("ssm")
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        region = boto3.Session().region_name

        kb_id = ssm.get_parameter(
            Name=f"/{account_id}-{region}/kb/knowledge-base-id"
        )["Parameter"]["Value"]

        bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=region)
        response = bedrock_agent.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": issue_description},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 3,
                    "overrideSearchType": "HYBRID",
                }
            },
        )

        results = []
        for result in response.get("retrievalResults", []):
            content = result.get("content", {}).get("text", "")
            score = result.get("score", 0)
            if content and score >= 0.4:
                results.append(content)

        if results:
            text = "\n\n---\n\n".join(results)
        else:
            text = (
                "No relevant technical documentation found for the described issue. "
                "Please contact our technical support team directly."
            )
    except Exception as e:
        print(f"Error in get_technical_support: {str(e)}")
        text = f"Unable to access technical support documentation. Error: {str(e)}"

    return {"content": [{"type": "text", "text": text}]}


# Convenience list of all tools
TOOLS = [get_return_policy, get_product_info, web_search, get_technical_support]
