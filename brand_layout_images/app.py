# %% [markdown]
# <h2>Generate branded product advertisement images with Replicate</h2>

import os
import sys

import streamlit as st
import replicate

# Works in both .py files and Jupyter notebooks
try:
    base_path = os.path.dirname(__file__)  # works in .py files
except NameError:
    base_path = os.getcwd()                # fallback for Jupyter notebooks

core_path = os.path.abspath(os.path.join(base_path, '..', 'core'))
sys.path.append(core_path)

from dotenv import load_dotenv
load_dotenv(override=True)

if not os.environ.get("REPLICATE_API_TOKEN"):
    raise RuntimeError("REPLICATE_API_TOKEN is not set. Add REPLICATE_API_TOKEN=<your replicate api key> to .env")

IMAGE_MODEL = "black-forest-labs/flux-2-pro"
DATA_FOLDER = os.path.join(base_path, "generated_images")

# --- predefined ad layout variations ---

VARIATION_TEMPLATES = {
    "Minimalist Studio": (
        "Professional studio product photography of a {product}, centered on a seamless "
        "neutral background, soft diffused lighting, subtle shadow, clean minimalist "
        "advertisement layout, high-end commercial photography, sharp focus, 8k"
    ),
    "Outdoor Lifestyle": (
        "Lifestyle advertisement photo of a {product} in a vibrant outdoor setting, natural "
        "sunlight, people enjoying the product in the background, energetic and aspirational "
        "mood, commercial ad photography"
    ),
    "Luxury Dark Mode": (
        "Luxury product advertisement of a {product} on a dark reflective surface, dramatic "
        "rim lighting, moody atmosphere, premium high-end branding aesthetic, cinematic shadows"
    ),
    "Bold Color Pop": (
        "Vibrant advertisement layout featuring a {product} against a bold solid color "
        "background with geometric shapes, modern graphic design elements, high contrast, "
        "playful energetic mood"
    ),
    "Festive Holiday": (
        "Holiday-themed advertisement of a {product} surrounded by festive decorations, warm "
        "string lights, seasonal props, cozy inviting atmosphere, commercial photography"
    ),
    "Tech Futuristic": (
        "Futuristic advertisement of a {product} with neon accent lighting, sleek tech "
        "background, holographic UI elements, cyberpunk aesthetic, high-tech commercial "
        "photography"
    ),
    "Nature & Eco": (
        "Eco-friendly advertisement of a {product} placed among natural elements like plants, "
        "wood, and stone, earthy tones, sustainable branding aesthetic, soft natural lighting"
    ),
    "E-commerce White Background": (
        "Clean e-commerce product shot of a {product} on a pure white background, even studio "
        "lighting, no shadow distractions, sharp detail, catalog-ready packshot photography"
    ),
    "Gradient Backdrop": (
        "Modern advertisement of a {product} floating against a smooth colorful gradient "
        "background, soft studio lighting, minimal shadow, trendy social media ad aesthetic"
    ),
    "Flat Lay": (
        "Top-down flat lay advertisement photo of a {product} arranged with complementary "
        "props on a styled surface, even overhead lighting, organized composition, editorial "
        "commercial photography"
    ),
    "Urban Street": (
        "Advertisement photo of a {product} in a gritty urban street setting, city backdrop, "
        "dramatic natural light, bold street-style mood, commercial lifestyle photography"
    ),
    "Retro Vintage": (
        "Vintage-inspired advertisement of a {product}, retro color grading, film grain, "
        "nostalgic 70s/80s aesthetic, classic print-ad composition"
    ),
    "Monochrome Editorial": (
        "High-fashion editorial advertisement of a {product} shot in dramatic black and white, "
        "strong contrast, sculptural lighting, premium magazine-ad composition"
    ),
    "Sale / Promo Banner": (
        "Eye-catching promotional advertisement banner featuring a {product}, bold sale "
        "typography space, bright energetic colors, dynamic diagonal composition, retail "
        "marketing ad layout"
    ),
    "Unboxing / Flat Box": (
        "Advertisement photo of a {product} styled as an unboxing scene with open packaging "
        "and box, soft top-down lighting, satisfying organized layout, commercial photography"
    ),
    "Social Proof Grid": (
        "Advertisement collage of a {product} shown from multiple angles in a clean grid "
        "layout, consistent studio lighting, product highlight callouts, modern app-store-style "
        "marketing composition"
    ),
}

ASPECT_RATIOS = {
    "1:1 (Square post)": "1:1",
    "4:5 (Feed portrait)": "4:5",
    "9:16 (Story/Reel)": "9:16",
    "16:9 (Banner)": "16:9",
}

DEFAULT_OPTION = "Default (from layout)"

CAMERA_ANGLES = {
    DEFAULT_OPTION: None,
    "Front-facing": "shot straight-on from the front",
    "3/4 Angle": "shot from a three-quarter angle",
    "Top-down": "shot from directly overhead",
    "Close-up Detail": "extreme close-up macro shot highlighting texture and detail",
    "Low Angle (Hero Shot)": "shot from a low angle looking up, heroic and imposing",
}

LIGHTING_MOODS = {
    DEFAULT_OPTION: None,
    "Soft & Bright": "soft, bright, evenly diffused lighting",
    "Dramatic & Moody": "dramatic, high-contrast moody lighting with deep shadows",
    "Golden Hour": "warm golden hour sunlight with long soft shadows",
    "Studio Flash": "crisp studio flash lighting with defined highlights",
    "Neon Glow": "colorful neon glow lighting",
}

BACKGROUND_ACCENTS = {
    DEFAULT_OPTION: None,
    "Pure White": "pure white background",
    "Solid Black": "solid black background",
    "Neutral Gray": "neutral gray background",
    "Pastel": "soft pastel-colored background",
    "Brand Color Accent": "background tinted with the product's brand color",
}

TARGET_PLATFORMS = {
    DEFAULT_OPTION: None,
    "Instagram / Facebook Ad": "optimized for an Instagram/Facebook social media ad",
    "Amazon / Marketplace Listing": "optimized for an Amazon marketplace product listing image",
    "Website Banner": "optimized for a website hero banner",
    "Print Catalog": "optimized for a print catalog advertisement",
}


# --- image generation (chat_/app.py generate_image logic) ---

def _download(url: str, dest_folder: str, default_name: str) -> str:
    import requests

    os.makedirs(dest_folder, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0] or default_name
    dest_path = os.path.join(dest_folder, filename)

    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return dest_path


def _extract_urls(output):
    if isinstance(output, str):
        return [output]
    if isinstance(output, list):
        return [str(item) for item in output]
    # replicate's FileOutput objects expose a .url attribute
    if hasattr(output, "url"):
        return [output.url]
    return [str(output)]


def generate_image(prompt: str, model: str = IMAGE_MODEL, dest_folder: str = DATA_FOLDER, **extra_args):
    extra_args.setdefault("output_format", "png")
    output = replicate.run(
        model,
        input={
            "prompt": prompt,
            **extra_args,
        },
    )

    urls = _extract_urls(output)
    return [_download(url, dest_folder, f"brand_image_{i}.png") for i, url in enumerate(urls)]


# --- Streamlit UI ---

st.set_page_config(page_title="Brand Layout Images", page_icon="🏷️")
st.title("Brand Layout Image Generator")
st.caption("Generate on-brand product advertisement images with Replicate.")

with st.form("brand_layout_form"):
    product = st.text_input("Product", placeholder="e.g. wireless bluetooth speaker")
    variation = st.selectbox("Ad layout variation", options=list(VARIATION_TEMPLATES.keys()))

    col1, col2 = st.columns(2)
    with col1:
        aspect_label = st.selectbox("Aspect ratio", options=list(ASPECT_RATIOS.keys()))
        camera_angle = st.selectbox("Camera angle", options=list(CAMERA_ANGLES.keys()))
        lighting = st.selectbox("Lighting mood", options=list(LIGHTING_MOODS.keys()))
    with col2:
        background = st.selectbox("Background accent", options=list(BACKGROUND_ACCENTS.keys()))
        platform = st.selectbox("Target platform", options=list(TARGET_PLATFORMS.keys()))

    ad_text = st.text_input(
        "Text to put on the image (optional)",
        placeholder="e.g. 50% OFF THIS WEEK",
    )
    extra_details = st.text_area(
        "Additional details (optional)", height=80,
        placeholder="e.g. matte black finish, brand color #1E90FF, add the logo in the corner",
    )
    submitted = st.form_submit_button("Generate", type="primary", disabled=False)

if submitted:
    if not product.strip():
        st.warning("Please enter a product first.")
    else:
        prompt = VARIATION_TEMPLATES[variation].format(product=product.strip())

        extra_descriptors = [
            CAMERA_ANGLES[camera_angle],
            LIGHTING_MOODS[lighting],
            BACKGROUND_ACCENTS[background],
            TARGET_PLATFORMS[platform],
        ]
        for descriptor in extra_descriptors:
            if descriptor:
                prompt = f"{prompt}, {descriptor}"

        if extra_details.strip():
            prompt = f"{prompt}, {extra_details.strip()}"

        if ad_text.strip():
            prompt = (
                f'{prompt}, with the text "{ad_text.strip()}" rendered clearly in bold, '
                "legible, well-kerned typography as part of the advertisement design"
            )

        with st.spinner("Generating image..."):
            paths = generate_image(prompt, aspect_ratio=ASPECT_RATIOS[aspect_label])
            local_path = paths[0]

        st.success("Done!")
        st.image(local_path, caption=f"{product} — {variation}")
        with st.expander("Prompt used"):
            st.write(prompt)
        with open(local_path, "rb") as f:
            st.download_button("Download image", f, file_name=os.path.basename(local_path))
