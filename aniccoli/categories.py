"""Asset category definitions and file-classification rules for Aniccoli."""

from enum import Enum
from pathlib import Path
from typing import Dict, Set, Union


PathInput = Union[str, Path]


class AssetCategory(str, Enum):
    """Categories supported by the Aniccoli asset organizer."""

    BLENDER = "Blender"
    MAYA = "Maya"

    FBX = "FBX Model"
    OBJ = "OBJ Model"
    GLTF = "GLTF Model"
    STL = "STL Model"
    OTHER_3D = "Other 3D Model"

    UNITY_SCENE = "Unity Scene"
    UNITY_PREFAB = "Unity Prefab"
    UNITY_MATERIAL = "Unity Material"
    UNITY_ANIMATION = "Unity Animation"
    UNITY_SCRIPT = "Unity Script"
    UNITY_OTHER = "Other Unity Asset"

    TEXTURE_BASE_COLOR = "Base Color Texture"
    TEXTURE_NORMAL = "Normal Texture"
    TEXTURE_ROUGHNESS = "Roughness Texture"
    TEXTURE_METALLIC = "Metallic Texture"
    TEXTURE_HEIGHT = "Height Texture"
    TEXTURE_AO = "Ambient Occlusion Texture"
    TEXTURE_OTHER = "Other Texture"

    REFERENCE = "Reference"
    RENDER = "Render"

    AUDIO = "Audio"
    VIDEO = "Video"
    DOCUMENT = "Document"
    ARCHIVE = "Archive"

    UNKNOWN = "Unknown"

    def __str__(self) -> str:
        """Return the readable category name."""
        return self.value


EXTENSION_CATEGORIES: Dict[str, AssetCategory] = {
    # Blender
    ".blend": AssetCategory.BLENDER,
    ".blend1": AssetCategory.BLENDER,
    ".blend2": AssetCategory.BLENDER,

    # Maya
    ".ma": AssetCategory.MAYA,
    ".mb": AssetCategory.MAYA,

    # Common 3D model formats
    ".fbx": AssetCategory.FBX,
    ".obj": AssetCategory.OBJ,
    ".gltf": AssetCategory.GLTF,
    ".glb": AssetCategory.GLTF,
    ".stl": AssetCategory.STL,

    # Other 3D production formats
    ".abc": AssetCategory.OTHER_3D,
    ".dae": AssetCategory.OTHER_3D,
    ".usd": AssetCategory.OTHER_3D,
    ".usda": AssetCategory.OTHER_3D,
    ".usdc": AssetCategory.OTHER_3D,
    ".3ds": AssetCategory.OTHER_3D,

    # Unity assets
    ".unity": AssetCategory.UNITY_SCENE,
    ".prefab": AssetCategory.UNITY_PREFAB,
    ".mat": AssetCategory.UNITY_MATERIAL,
    ".anim": AssetCategory.UNITY_ANIMATION,
    ".controller": AssetCategory.UNITY_ANIMATION,
    ".overridecontroller": AssetCategory.UNITY_ANIMATION,
    ".cs": AssetCategory.UNITY_SCRIPT,
    ".shader": AssetCategory.UNITY_SCRIPT,
    ".compute": AssetCategory.UNITY_SCRIPT,
    ".asset": AssetCategory.UNITY_OTHER,
    ".asmdef": AssetCategory.UNITY_OTHER,
    ".meta": AssetCategory.UNITY_OTHER,

    # Audio
    ".mp3": AssetCategory.AUDIO,
    ".wav": AssetCategory.AUDIO,
    ".ogg": AssetCategory.AUDIO,
    ".flac": AssetCategory.AUDIO,
    ".aac": AssetCategory.AUDIO,
    ".m4a": AssetCategory.AUDIO,

    # Video
    ".mp4": AssetCategory.VIDEO,
    ".mov": AssetCategory.VIDEO,
    ".avi": AssetCategory.VIDEO,
    ".mkv": AssetCategory.VIDEO,
    ".webm": AssetCategory.VIDEO,

    # Documents
    ".pdf": AssetCategory.DOCUMENT,
    ".doc": AssetCategory.DOCUMENT,
    ".docx": AssetCategory.DOCUMENT,
    ".txt": AssetCategory.DOCUMENT,
    ".md": AssetCategory.DOCUMENT,
    ".rtf": AssetCategory.DOCUMENT,
    ".csv": AssetCategory.DOCUMENT,
    ".xlsx": AssetCategory.DOCUMENT,
    ".pptx": AssetCategory.DOCUMENT,

    # Archives
    ".zip": AssetCategory.ARCHIVE,
    ".rar": AssetCategory.ARCHIVE,
    ".7z": AssetCategory.ARCHIVE,
    ".tar": AssetCategory.ARCHIVE,
    ".gz": AssetCategory.ARCHIVE,
}


IMAGE_EXTENSIONS: Set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tga",
    ".exr",
    ".hdr",
    ".psd",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
}


BASE_COLOR_KEYWORDS = {
    "basecolor",
    "base_color",
    "basecolour",
    "base_colour",
    "albedo",
    "diffuse",
}

NORMAL_KEYWORDS = {
    "normal",
    "normalmap",
    "normal_map",
    "nrm",
}

ROUGHNESS_KEYWORDS = {
    "roughness",
    "rough",
    "rgh",
}

METALLIC_KEYWORDS = {
    "metallic",
    "metalness",
    "metal_map",
}

HEIGHT_KEYWORDS = {
    "height",
    "heightmap",
    "height_map",
    "displacement",
    "disp",
    "bump",
}

AO_KEYWORDS = {
    "ambientocclusion",
    "ambient_occlusion",
    "occlusion",
    "ao_map",
}

RENDER_KEYWORDS = {
    "render",
    "final_render",
    "beauty",
    "output",
    "frame",
}

REFERENCE_KEYWORDS = {
    "reference",
    "references",
    "ref",
    "concept",
    "moodboard",
    "inspiration",
    "sketch",
}


CATEGORY_FOLDERS: Dict[AssetCategory, Path] = {
    AssetCategory.BLENDER: Path("3D_Models") / "Blender",
    AssetCategory.MAYA: Path("3D_Models") / "Maya",

    AssetCategory.FBX: Path("3D_Models") / "FBX",
    AssetCategory.OBJ: Path("3D_Models") / "OBJ",
    AssetCategory.GLTF: Path("3D_Models") / "GLTF",
    AssetCategory.STL: Path("3D_Models") / "STL",
    AssetCategory.OTHER_3D: Path("3D_Models") / "Other",

    AssetCategory.UNITY_SCENE: Path("Unity") / "Scenes",
    AssetCategory.UNITY_PREFAB: Path("Unity") / "Prefabs",
    AssetCategory.UNITY_MATERIAL: Path("Unity") / "Materials",
    AssetCategory.UNITY_ANIMATION: Path("Unity") / "Animations",
    AssetCategory.UNITY_SCRIPT: Path("Unity") / "Scripts",
    AssetCategory.UNITY_OTHER: Path("Unity") / "Other",

    AssetCategory.TEXTURE_BASE_COLOR: Path("Textures") / "Base_Color",
    AssetCategory.TEXTURE_NORMAL: Path("Textures") / "Normal",
    AssetCategory.TEXTURE_ROUGHNESS: Path("Textures") / "Roughness",
    AssetCategory.TEXTURE_METALLIC: Path("Textures") / "Metallic",
    AssetCategory.TEXTURE_HEIGHT: Path("Textures") / "Height",
    AssetCategory.TEXTURE_AO: Path("Textures") / "Ambient_Occlusion",
    AssetCategory.TEXTURE_OTHER: Path("Textures") / "Other",

    AssetCategory.REFERENCE: Path("References"),
    AssetCategory.RENDER: Path("Renders"),

    AssetCategory.AUDIO: Path("Audio"),
    AssetCategory.VIDEO: Path("Videos"),
    AssetCategory.DOCUMENT: Path("Documents"),
    AssetCategory.ARCHIVE: Path("Archives"),

    AssetCategory.UNKNOWN: Path("Unknown"),
}


def _normalize_filename(file_path: Path) -> str:
    """Create a lowercase filename that is easier to search for keywords."""
    normalized_name = file_path.stem.lower()

    normalized_name = normalized_name.replace("-", "_")
    normalized_name = normalized_name.replace(" ", "_")
    normalized_name = normalized_name.replace(".", "_")

    return normalized_name


def _contains_keyword(filename: str, keywords: Set[str]) -> bool:
    """Return True when the filename contains one of the supplied keywords."""
    return any(keyword in filename for keyword in keywords)


def _classify_image(file_path: Path) -> AssetCategory:
    """Classify an image as a texture, render, or reference."""
    normalized_name = _normalize_filename(file_path)

    if _contains_keyword(normalized_name, BASE_COLOR_KEYWORDS):
        return AssetCategory.TEXTURE_BASE_COLOR

    if _contains_keyword(normalized_name, NORMAL_KEYWORDS):
        return AssetCategory.TEXTURE_NORMAL

    if _contains_keyword(normalized_name, ROUGHNESS_KEYWORDS):
        return AssetCategory.TEXTURE_ROUGHNESS

    if _contains_keyword(normalized_name, METALLIC_KEYWORDS):
        return AssetCategory.TEXTURE_METALLIC

    if _contains_keyword(normalized_name, HEIGHT_KEYWORDS):
        return AssetCategory.TEXTURE_HEIGHT

    if _contains_keyword(normalized_name, AO_KEYWORDS):
        return AssetCategory.TEXTURE_AO

    if _contains_keyword(normalized_name, RENDER_KEYWORDS):
        return AssetCategory.RENDER

    if _contains_keyword(normalized_name, REFERENCE_KEYWORDS):
        return AssetCategory.REFERENCE

    return AssetCategory.TEXTURE_OTHER


def classify_file(file_path: PathInput) -> AssetCategory:
    """
    Identify the asset category of a file.

    The function checks the file extension first. Image files receive
    additional filename analysis to identify texture maps and renders.
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension in IMAGE_EXTENSIONS:
        return _classify_image(path)

    return EXTENSION_CATEGORIES.get(
        extension,
        AssetCategory.UNKNOWN,
    )


def destination_folder(category: AssetCategory) -> Path:
    """Return the relative destination folder for an asset category."""
    return CATEGORY_FOLDERS[category]