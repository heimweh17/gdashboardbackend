"""
Gemini AI service for generating insights from analysis results.
"""
import json
import os
from typing import Any, Dict

try:
	import google.generativeai as genai
	from google.generativeai.types import HarmCategory, HarmBlockThreshold
	GEMINI_AVAILABLE = True
except ImportError:
	GEMINI_AVAILABLE = False

from app.core.config import settings


def _get_available_models() -> list[str]:
	"""
	List available Gemini models for generateContent.
	Returns list of model names that support generateContent.
	"""
	if not GEMINI_AVAILABLE:
		return []
	
	if not settings.gemini_api_key:
		return []
	
	try:
		genai.configure(api_key=settings.gemini_api_key)
		models = genai.list_models()
		
		available = []
		for model in models:
			# Check if model supports generateContent
			if "generateContent" in model.supported_generation_methods:
				# Extract just the model name (remove 'models/' prefix if present)
				name = model.name
				if name.startswith("models/"):
					name = name[7:]  # Remove "models/" prefix
				available.append(name)
				# Also add with prefix for compatibility
				if not name.startswith("models/"):
					available.append(f"models/{name}")
		
		return available
	except Exception:
		return []


def _find_working_model(preferred: str) -> str:
	"""
	Find a working model by checking available models.
	Returns the preferred model if available, otherwise returns first available model.
	"""
	available = _get_available_models()
	
	if not available:
		# Fallback to common model names if list_models fails
		return preferred
	
	# Check if preferred model is available (with or without models/ prefix)
	preferred_variants = [preferred, f"models/{preferred}"]
	if preferred.startswith("models/"):
		preferred_variants = [preferred, preferred[7:]]
	
	for variant in preferred_variants:
		if variant in available:
			return variant
	
	# Return first available model
	return available[0] if available else preferred


def generate_insight(analysis_result: Dict[str, Any], context: Dict[str, Any] | None = None) -> Dict[str, Any]:
	"""
	Generate AI insight from analysis result using Gemini.
	
	Args:
		analysis_result: The analysis result dict (summary, grid_density, clustering)
		context: Optional context dict (city_name, filters, viewport_bbox)
	
	Returns:
		Dict with 'text', 'highlights', and 'method' keys
	"""
	if not GEMINI_AVAILABLE:
		raise RuntimeError("google-generativeai package not installed")
	
	if not settings.gemini_api_key:
		raise ValueError("GEMINI_API_KEY not configured")
	
	genai.configure(api_key=settings.gemini_api_key)
	
	# Find a working model by checking available models
	model_name = _find_working_model(settings.gemini_model)
	
	# Try to create model
	try:
		model = genai.GenerativeModel(
			model_name=model_name,
			safety_settings={
				HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
				HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
				HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
				HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
			},
		)
	except Exception as e:
		# If still fails, try fallback models
		fallback_models = ["gemini-1.5-pro", "gemini-1.0-pro", "gemini-pro"]
		model = None
		last_error = str(e)
		
		for fallback in fallback_models:
			try:
				# Try both with and without models/ prefix
				for variant in [fallback, f"models/{fallback}"]:
					try:
						model = genai.GenerativeModel(
							model_name=variant,
							safety_settings={
								HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
								HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
								HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
								HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
							},
						)
						model_name = variant
						break
					except Exception:
						continue
				if model:
					break
			except Exception:
				continue
		
		if model is None:
			available_models = _get_available_models()
			available_str = ", ".join(available_models[:5]) if available_models else "none found"
			raise RuntimeError(
				f"Failed to initialize Gemini model. Original error: {last_error}. "
				f"Tried: {settings.gemini_model}, {model_name}, and fallbacks. "
				f"Available models: {available_str}"
			)
	
	# Build prompt
	prompt = _build_prompt(analysis_result, context)
	
	# Generate response
	response = model.generate_content(
		prompt,
		generation_config={
			"temperature": 0.7,
			"max_output_tokens": settings.ai_max_output_tokens,
		},
	)
	
	# Parse JSON response
	text = response.text.strip()
	
	# Try to extract JSON if wrapped in markdown code blocks
	if "```json" in text:
		start = text.find("```json") + 7
		end = text.find("```", start)
		if end > start:
			text = text[start:end].strip()
	elif "```" in text:
		start = text.find("```") + 3
		end = text.find("```", start)
		if end > start:
			text = text[start:end].strip()
	
	try:
		result = json.loads(text)
	except json.JSONDecodeError:
		# Fallback: return as plain text with basic structure
		result = {
			"text": text,
			"highlights": [text[:100] + "..." if len(text) > 100 else text],
			"method": "Gemini analysis based on provided data",
		}
	
	# Ensure required fields
	if "text" not in result:
		result["text"] = text
	if "highlights" not in result or not isinstance(result["highlights"], list):
		result["highlights"] = [result.get("text", text)[:100] + "..."]
	if "method" not in result:
		result["method"] = "Gemini analysis based on provided data"
	
	return result


def _build_prompt(analysis_result: Dict[str, Any], context: Dict[str, Any] | None = None) -> str:
	"""Build the prompt for Gemini."""
	
	summary = analysis_result.get("summary", {})
	clustering = analysis_result.get("clustering", {})
	grid = analysis_result.get("grid_density", {})
	
	# Extract key metrics
	total_points = summary.get("total_points", 0)
	category_counts = summary.get("category_counts", {})
	bbox = summary.get("bbox")
	mean_center = summary.get("mean_center")
	num_clusters = clustering.get("num_clusters", 0)
	num_noise = clustering.get("num_noise", 0)
	clusters = clustering.get("clusters", [])
	
	prompt_parts = [
		"You are a geospatial data analyst. Analyze the following geospatial analysis results and provide insights.",
		"",
		"CRITICAL RULES:",
		"1. DO NOT invent or make up any data. Only reference fields that are present in the analysis_result.",
		"2. Use hedging language: 'suggests', 'may indicate', 'appears to', 'likely', 'possibly'.",
		"3. Include numeric proportions when available (percentages, counts).",
		"4. If data is missing, explicitly state that limitation.",
		"",
		"ANALYSIS DATA:",
		f"- Total points: {total_points}",
	]
	
	if category_counts:
		# Sort by count and show top categories
		sorted_cats = sorted(category_counts.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)
		prompt_parts.append("- Category distribution:")
		for cat, count in sorted_cats[:10]:  # Top 10
			pct = (count / total_points * 100) if total_points > 0 else 0
			prompt_parts.append(f"  * {cat}: {count} ({pct:.1f}%)")
	else:
		prompt_parts.append("- Category counts: Not available")
	
	if bbox:
		prompt_parts.append(f"- Bounding box: {json.dumps(bbox)}")
	
	if mean_center:
		prompt_parts.append(f"- Mean center: {json.dumps(mean_center)}")
	
	prompt_parts.append(f"- Clustering: {num_clusters} clusters, {num_noise} noise points")
	
	if clusters:
		largest = max(clusters, key=lambda c: c.get("size", 0), default=None)
		if largest:
			prompt_parts.append(f"- Largest cluster: size {largest.get('size', 0)} at {json.dumps(largest.get('centroid', {}))}")
	
	if context:
		if context.get("city_name"):
			prompt_parts.append(f"- Context: City: {context['city_name']}")
		if context.get("viewport_bbox"):
			prompt_parts.append(f"- Viewport: {json.dumps(context['viewport_bbox'])}")
	
	prompt_parts.extend([
		"",
		"OUTPUT FORMAT: Return a JSON object with exactly these fields:",
		"{",
		'  "text": "A concise scientific-style narrative paragraph (3-5 sentences) summarizing the spatial patterns, distribution characteristics, and notable findings. Use hedging language and reference specific numbers from the data.",',
		'  "highlights": ["Bullet point 1 with key finding and %", "Bullet point 2", "Bullet point 3"],',
		'  "method": "Brief note on methodology/assumptions (e.g., DBSCAN clustering, category field used, spatial extent)"',
		"}",
		"",
		"Generate the insight now:",
	])
	
	return "\n".join(prompt_parts)

