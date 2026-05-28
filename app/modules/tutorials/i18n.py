from typing import Dict, List, Optional


SUPPORTED_TUTORIAL_LOCALES = {"zh", "en"}
DEFAULT_TUTORIAL_LOCALE = "zh"


def normalize_tutorial_locale(locale: Optional[str]) -> str:
    if locale in SUPPORTED_TUTORIAL_LOCALES:
        return locale
    return DEFAULT_TUTORIAL_LOCALE


AUTHOR_BY_LOCALE = {
    "zh": {
        "id": "ai-skill-editorial",
        "name": "Skillnetic 团队",
        "avatarUrl": None,
        "title": "官方编辑",
    },
    "en": {
        "id": "ai-skill-editorial",
        "name": "Skillnetic Team",
        "avatarUrl": None,
        "title": "Editorial Team",
    },
}


TUTORIAL_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "chatgpt-prompt-beginner": {
        "title_en": "ChatGPT Prompt Basics: From One Sentence to a High-Quality Prompt",
        "summary_en": "Learn how to write stable, reusable prompts through role setup, task framing, constraints, and structure so AI outputs become more accurate and useful.",
        "keywords_en": "ChatGPT prompt prompt basics beginner",
    },
    "midjourney-guide-complete": {
        "title_en": "The Complete Midjourney Guide: From Beginner to Advanced",
        "summary_en": "From account setup and interface basics to prompt structure, style control, parameters, and upscaling, this guide covers the full Midjourney workflow.",
        "keywords_en": "Midjourney guide AI design image generation",
    },
    "n8n-workflow-automation": {
        "title_en": "Workflow Practice: Automate Tasks with n8n",
        "summary_en": "Use three practical cases to understand key n8n nodes and workflow design patterns so you can automate recurring tasks and improve efficiency.",
        "keywords_en": "n8n workflow automation agent",
    },
    "excel-ai-data-analysis": {
        "title_en": "Excel + AI Data Analysis: From Raw Data to Insights",
        "summary_en": "Combine AI tools with Excel to clean data, analyze trends, and build visualizations faster so you can turn spreadsheets into useful insights.",
        "keywords_en": "Excel AI data analysis insights",
    },
    "xiaohongshu-ai-content-guide": {
        "title_en": "The Complete AI Xiaohongshu Content Playbook",
        "summary_en": "Use AI to improve topic selection, titles, body copy, and cover ideas so you can produce Xiaohongshu content more efficiently.",
        "keywords_en": "Xiaohongshu AI content creation operations",
    },
    "python-ai-app-practice": {
        "title_en": "Python + AI Practice: Build Intelligent Applications",
        "summary_en": "Use Python with the OpenAI API to quickly build chatbots, text analysis tools, and other practical AI-powered applications.",
        "keywords_en": "Python AI OpenAI API intelligent applications",
    },
}


TUTORIAL_CATEGORY_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "beginner": {"name_en": "Beginner Tutorials"},
    "prompt": {"name_en": "Prompt Techniques"},
    "tools": {"name_en": "Tool Usage"},
    "workflow": {"name_en": "Workflow Building"},
    "industry": {"name_en": "Industry Use Cases"},
    "advanced": {"name_en": "Advanced Growth"},
    "cases": {"name_en": "Case Studies"},
}


TUTORIAL_TAG_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "chatgpt": {"name_en": "ChatGPT"},
    "prompt": {"name_en": "Prompt"},
    "midjourney": {"name_en": "Midjourney"},
    "workflow": {"name_en": "Workflow"},
    "excel": {"name_en": "Excel"},
    "data-analysis": {"name_en": "Data Analysis"},
    "xiaohongshu": {"name_en": "Xiaohongshu"},
    "python": {"name_en": "Python"},
    "ai-api": {"name_en": "AI API"},
    "automation": {"name_en": "Automation"},
    "agent": {"name_en": "Agent"},
    "office-efficiency": {"name_en": "Office Efficiency"},
    "content-creation": {"name_en": "Content Creation"},
    "operations": {"name_en": "Operations"},
    "design": {"name_en": "Design"},
    "coding": {"name_en": "Coding"},
}


LEARNING_PATH_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ai-beginner-path": {
        "title_en": "AI Beginner Path",
        "description_en": "Start from zero and quickly build core AI skills.",
    },
    "prompt-advanced-path": {
        "title_en": "Prompt Mastery Path",
        "description_en": "Learn high-quality prompt writing and practical prompt techniques.",
    },
    "workflow-practice-path": {
        "title_en": "Workflow Practice Path",
        "description_en": "Move from automation to intelligent agents and build efficient workflows.",
    },
    "industry-application-path": {
        "title_en": "Industry Application Path",
        "description_en": "Explore practical AI use cases and industry examples.",
    },
}


TUTORIAL_DETAIL_TRANSLATIONS: Dict[str, Dict[str, object]] = {
    "chatgpt-prompt-beginner": {
        "learning_points_en": [
            "Understand the core structure and design principles of prompts",
            "Use a practical four-step method to write higher-quality prompts",
            "Improve prompts through before-and-after comparisons",
            "Avoid common beginner mistakes and unstable outputs",
        ],
        "suitable_for_en": [
            "Beginners who want to get started with ChatGPT quickly",
            "Users who want AI to produce more stable and structured results",
            "Creators, operators, designers, and developers who rely on repeatable prompts",
        ],
        "seo_title_en": "ChatGPT Prompt Basics Tutorial",
        "seo_description_en": "Learn the structure, examples, and optimization method behind high-quality ChatGPT prompts.",
        "content_markdown_en": """## 1. What is a prompt?

A prompt is the instruction you give to an AI model. A good prompt helps the model understand your role, task, constraints, and expected output format.

Without that structure, the output often becomes generic, unstable, or too broad.

> Tip: a better prompt is not always a longer prompt. It should be clearer, more concrete, and easier to execute.

## 2. The four-part prompt structure

### Role setup

Tell the model who it should act as, such as a marketing strategist, data analyst, or writing coach.

### Task description

Describe the exact problem to solve. Be explicit about the scenario, audience, and goal.

### Output format

Specify whether you want a list, table, paragraph, JSON format, or a step-by-step answer.

### Constraints and examples

Add limits like tone, length, forbidden content, and a short example when needed.

## 3. A weak prompt vs. a stronger prompt

Weak prompt:

> Help me write a Xiaohongshu post.

Stronger prompt:

> You are an experienced Xiaohongshu editor. Write a post for beginner office workers about using AI to improve efficiency. Use a conversational tone, give 3 practical tips, and end with a short action summary.

The stronger version gives the model enough context to produce something more usable.

## 4. Common mistakes to avoid

- Asking for something broad without context
- Forgetting to define the audience
- Omitting output format requirements
- Reusing the same prompt without iterating on examples and constraints

## 5. What to practice next

Take one recurring task from your work and rewrite the prompt with role, task, format, and constraints. That single change often improves output quality immediately.""",
        "prompt_blocks_en": [
            {
                "title": "Xiaohongshu post prompt",
                "description": "Use it directly in ChatGPT",
                "content": "You are an experienced Xiaohongshu content strategist. Write a post about how AI improves work efficiency for beginner office workers. Requirements:\\n1. Identify the target audience clearly\\n2. Use a conversational and natural tone\\n3. Include 3 practical tips and a short conclusion\\n4. Keep the post under 800 Chinese characters",
            }
        ],
    },
    "midjourney-guide-complete": {
        "learning_points_en": [
            "Understand the basic Midjourney workflow from prompt to upscale",
            "Learn how style words and parameters change image output",
            "Build a reusable prompt structure for visual generation tasks",
        ],
        "suitable_for_en": [
            "Designers and creators starting with AI image generation",
            "Users who want more control over style consistency",
            "Teams that need faster visual ideation",
        ],
        "seo_title_en": "Midjourney Complete Guide",
        "seo_description_en": "A practical Midjourney guide covering prompts, style control, parameters, and iteration.",
        "content_markdown_en": """## 1. Start with a simple workflow

The basic Midjourney loop is simple: write a prompt, review four results, choose a direction, and iterate.

You do not need a perfect prompt on the first try. The first goal is to establish subject, scene, and style.

## 2. Build prompts with stable components

Use a structure like:

- Subject
- Scene
- Style
- Lighting
- Camera or composition
- Parameters

This keeps your iterations easier to compare.

## 3. Use style words carefully

Style words such as cinematic, editorial, minimal, or watercolor can change the result dramatically. Add only one or two major style directions at a time.

## 4. Parameters are for control

Parameters like aspect ratio, stylize, or chaos should be used intentionally. If you change too many at once, you will not know what improved the image.

## 5. Iterate with purpose

Save strong prompt fragments, note what changed each round, and reuse successful structures for the next project.""",
        "prompt_blocks_en": [
            {
                "title": "Product visual prompt",
                "description": "Good for testing composition and style",
                "content": "A premium wireless headset on a clean desk, soft daylight, minimal editorial style, realistic materials, shallow depth of field, high detail --ar 4:5 --stylize 150",
            }
        ],
    },
    "n8n-workflow-automation": {
        "learning_points_en": [
            "Understand how triggers, actions, and logic nodes work together",
            "Design workflows that are easier to test and maintain",
            "Use AI steps only where they add clear value",
        ],
        "suitable_for_en": [
            "Operators building repeatable automation",
            "Teams connecting forms, sheets, and notifications",
            "Users exploring AI agents on top of workflows",
        ],
        "seo_title_en": "n8n Workflow Automation Tutorial",
        "seo_description_en": "Learn how to design practical n8n workflows with stable triggers, branches, and AI steps.",
        "content_markdown_en": """## 1. Think in input, logic, and output

Every workflow should start with a clear trigger, move through a small number of decisions, and end with a measurable output.

## 2. Keep each workflow focused

Avoid building one giant workflow that does everything. Smaller workflows are easier to debug and reuse.

## 3. Add AI only to uncertain steps

AI is useful for classification, rewriting, summarization, and extraction. It is not a replacement for deterministic routing logic.

## 4. Test each branch independently

Use sample data and isolate critical nodes before connecting the full chain. This saves a lot of debugging time later.

## 5. Monitor and improve

Track which steps fail most often, where manual fixes happen, and which prompts need tightening. Stable automation is built through iteration.""",
        "prompt_blocks_en": [
            {
                "title": "Email classification prompt",
                "description": "Useful inside an n8n AI node",
                "content": "Classify the following email into one of these labels: sales, support, billing, partnership, spam. Return only valid JSON with label and confidence.",
            }
        ],
    },
    "excel-ai-data-analysis": {
        "learning_points_en": [
            "Use AI to speed up data cleaning and summary generation",
            "Combine spreadsheet formulas with AI reasoning effectively",
            "Turn rough data into clear business insights faster",
        ],
        "suitable_for_en": [
            "Operators and analysts working with repetitive spreadsheets",
            "Business users who need faster first-pass analysis",
            "Teams preparing weekly or monthly reports",
        ],
        "seo_title_en": "Excel and AI Data Analysis Tutorial",
        "seo_description_en": "A practical guide to using AI with Excel for cleaning, analysis, and reporting.",
        "content_markdown_en": """## 1. Start with clean data

Before asking AI for analysis, make sure column names, date formats, and missing values are consistent.

## 2. Let Excel handle structure

Use Excel for sorting, filtering, formulas, and quick pivots. Let AI help with interpretation, explanation, and pattern finding.

## 3. Ask focused analytical questions

Instead of saying “analyze this table,” ask for trends, anomalies, segments, or a concise report summary.

## 4. Validate important conclusions

AI can summarize patterns quickly, but final business decisions should still be checked against the raw numbers.

## 5. Build a repeatable reporting flow

Once you find a prompt and report structure that works, turn it into a reusable template for your team.""",
        "prompt_blocks_en": [
            {
                "title": "Report summary prompt",
                "description": "Turn a table into an executive summary",
                "content": "You are a business analyst. Based on the following sales table, summarize the top 3 trends, the biggest anomaly, and 2 suggested follow-up actions. Keep the output concise and business-friendly.",
            }
        ],
    },
    "xiaohongshu-ai-content-guide": {
        "learning_points_en": [
            "Use AI across topic selection, titles, body copy, and cover ideas",
            "Keep AI outputs aligned with platform tone and audience needs",
            "Turn content production into a repeatable workflow",
        ],
        "suitable_for_en": [
            "Creators and operators publishing on Xiaohongshu",
            "Small teams with limited content capacity",
            "Brands testing AI-assisted content workflows",
        ],
        "seo_title_en": "AI Xiaohongshu Content Guide",
        "seo_description_en": "Learn how to use AI for Xiaohongshu topics, titles, structure, and production workflows.",
        "content_markdown_en": """## 1. AI helps before writing starts

The biggest time savings often come from topic research, audience pain points, and title directions, not just body copy generation.

## 2. Keep a clear account voice

Define your account tone, audience, and content format before asking AI to write. Otherwise the output becomes generic.

## 3. Use title batches and angle tests

Generate several title directions, then compare curiosity, clarity, and conversion potential.

## 4. Turn long writing into modular steps

Draft outline first, then expand sections, then polish transitions, and finally generate cover copy.

## 5. Review with platform judgment

AI can speed up production, but final content still needs human review for authenticity, rhythm, and platform fit.""",
        "prompt_blocks_en": [
            {
                "title": "Title brainstorming prompt",
                "description": "Generate multiple content angles first",
                "content": "You are a Xiaohongshu growth editor. Generate 12 title options for a post about improving office efficiency with AI. Mix practical, emotional, and curiosity-driven angles. Avoid clickbait.",
            }
        ],
    },
    "python-ai-app-practice": {
        "learning_points_en": [
            "Understand the minimum building blocks of an AI app",
            "Use Python to connect prompts, APIs, and structured outputs",
            "Move from prototypes to more reliable application patterns",
        ],
        "suitable_for_en": [
            "Developers building their first AI-powered product",
            "Engineers integrating LLM features into internal tools",
            "Makers validating ideas quickly",
        ],
        "seo_title_en": "Python AI Application Practice Tutorial",
        "seo_description_en": "Use Python and the OpenAI API to prototype and structure practical AI applications quickly.",
        "content_markdown_en": """## 1. Start with one narrow use case

A good AI app usually begins with one focused task such as summarization, classification, extraction, or question answering.

## 2. Separate prompt logic from application logic

Keep prompts in clear templates and keep Python responsible for input validation, retries, and result handling.

## 3. Prefer structured outputs

If the downstream step needs fields, labels, or scores, request structured JSON instead of plain prose.

## 4. Add logging and guardrails early

Record failures, ambiguous inputs, and bad outputs from the start. That makes the system much easier to improve.

## 5. Optimize after the loop works

Get the full request-response loop working first. Then improve prompts, latency, caching, and user experience.""",
        "prompt_blocks_en": [
            {
                "title": "Structured extraction prompt",
                "description": "Useful for Python + LLM pipelines",
                "content": "Extract the customer name, product, urgency, and requested action from the message below. Return valid JSON only.",
            }
        ],
    },
}


HOT_KEYWORDS_BY_LOCALE = {
    "zh": [
        "ChatGPT 提示词",
        "Midjourney 绘图",
        "工作流搭建",
        "Excel + AI",
        "Agent 搭建",
        "小红书运营",
    ],
    "en": [
        "ChatGPT prompts",
        "Midjourney art",
        "Workflow building",
        "Excel + AI",
        "Agent setup",
        "Xiaohongshu growth",
    ],
}


DIFFICULTY_LABELS_BY_LOCALE = {
    "zh": {
        "beginner": "新手",
        "intermediate": "进阶",
        "advanced": "专业",
    },
    "en": {
        "beginner": "Beginner",
        "intermediate": "Intermediate",
        "advanced": "Advanced",
    },
}


def get_detail_translation(slug: str, locale: str) -> Dict[str, object]:
    if locale == DEFAULT_TUTORIAL_LOCALE:
        return {}
    return TUTORIAL_DETAIL_TRANSLATIONS.get(slug, {})


def get_localized_list(detail: Dict[str, object], key: str) -> Optional[List[str]]:
    value = detail.get(key)
    if isinstance(value, list):
        return [str(item) for item in value]
    return None
