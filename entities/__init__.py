"""
Entities module - Bevat alle game entities.

Dit omvat characters, platforms, attacks en andere game objecten.
"""

from entities.base_character import BaseCharacter
from entities.warrior import Warrior
from entities.mage import Mage
from entities.ninja import Ninja
from entities.platform import Platform
from entities.attack import Attack, Hitbox

__all__ = [
    'BaseCharacter',
    'Warrior',
    'Mage', 
    'Ninja',
    'Platform',
    'Attack',
    'Hitbox',
]
