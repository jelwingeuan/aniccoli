"""Every asset category must map to one of the coloured groups."""

from aniccoli.app import CATEGORY_GROUP_COLORS, _category_group
from aniccoli.categories import AssetCategory


def test_every_category_has_a_colour_group() -> None:
    for category in AssetCategory:
        assert _category_group(category) in CATEGORY_GROUP_COLORS


def test_category_groups() -> None:
    assert _category_group(AssetCategory.BLENDER) == "scenes"
    assert _category_group(AssetCategory.UNITY_SCENE) == "scenes"
    assert _category_group(AssetCategory.OTHER_3D) == "models"
    assert _category_group(AssetCategory.TEXTURE_AO) == "textures"
    assert _category_group(AssetCategory.UNITY_SCRIPT) == "unity"
    assert _category_group(AssetCategory.VIDEO) == "media"
    assert _category_group(AssetCategory.UNKNOWN) == "other"
