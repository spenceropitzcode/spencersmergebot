"""
Troop Definitions for Merge Tactics Game Board Reading

This module defines all troops with their characteristics including:
- Stars (merge level: 1-4 stars)
- Cost (elixir cost)
- Traits (special abilities/characteristics)
- Name (display name)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class MergeLevel(Enum):
    """Troop merge levels (stars)"""
    ONE_STAR = 1
    TWO_STAR = 2
    THREE_STAR = 3
    FOUR_STAR = 4

class Traits(Enum):
    ACE = 1
    ASSASSIN = 2
    AVENGER = 3
    BRAWLER = 4
    CLAN = 5
    GOBLIN = 6
    JUGGERNAUT = 7
    NOBLE = 8
    RANGER = 9
    THROWER = 10
    UNDEAD = 11

@dataclass
class Troop:
    """Base troop class with essential properties for Merge Tactics"""
    name: str
    cost: int  # Elixir cost
    stars: MergeLevel  # Merge level (1-4 stars)
    traits: List[Traits]  # Special abilities/characteristics
    
    def __str__(self):
        return f"{self.name} ({self.cost} elixir, {self.stars.value}⭐)"
    
    def __repr__(self):
        return f"Troop(name='{self.name}', cost={self.cost}, stars={self.stars.value})"

class TroopRegistry:
    """Registry containing all troop definitions"""
    
    def __init__(self):
        self.troops: Dict[str, Troop] = {}
        self._initialize_troops()
    
    def _initialize_troops(self):

        self.troops["archer"] = Troop(
            name="Archer",
            cost=2,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.CLAN, Traits.RANGER]
        )
        
        self.troops["barbarian"] = Troop(
            name="Barbarian",
            cost=2,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.BRAWLER, Traits.CLAN]
        )
        
        self.troops["bomber"] = Troop(
            name="Bomber",
            cost=2,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.THROWER, Traits.UNDEAD]
        )
        
        self.troops["goblin"] = Troop(
            name="Goblin",
            cost=2,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.GOBLIN, Traits.ASSASSIN]
        )
        
        self.troops["knight"] = Troop(
            name="Knight",
            cost=2,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.NOBLE, Traits.JUGGERNAUT]
        )
        
        self.troops["spear_goblin"] = Troop(
            name="Spear Goblin",
            cost=2,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.THROWER, Traits.GOBLIN]
        )
        
        self.troops["giant_skeleton"] = Troop(
            name="Giant Skeleton",
            cost=3,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.BRAWLER, Traits.UNDEAD]
        )
        
        self.troops["valkyrie"] = Troop(
            name="Valkyrie",
            cost=3,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.CLAN, Traits.AVENGER]
        )
        
        self.troops["pekka"] = Troop(
            name="P.E.K.K.A",
            cost=3,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.JUGGERNAUT, Traits.ACE]
        )
        
        self.troops["prince"] = Troop(
            name="Prince",
            cost=3,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.NOBLE, Traits.BRAWLER]
        )
        
        self.troops["dart_goblin"] = Troop(
            name="Dart Goblin",
            cost=3,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.RANGER, Traits.GOBLIN]
        )
        
        self.troops["executioner"] = Troop(
            name="Executioner",
            cost=3,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.THROWER, Traits.ACE]
        )
        
        self.troops["goblin_machine"] = Troop(
            name="Goblin Machine",
            cost=4,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.JUGGERNAUT, Traits.GOBLIN]
        )
        
        self.troops["princess"] = Troop(
            name="Princess",
            cost=4,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.RANGER, Traits.NOBLE]
        )
        
        self.troops["bandit"] = Troop(
            name="Bandit",
            cost=4,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.ACE, Traits.AVENGER]
        )
        
        self.troops["royal_ghost"] = Troop(
            name="Royal Ghost",
            cost=4,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.UNDEAD, Traits.ASSASSIN]
        )
        
        self.troops["mega_knight"] = Troop(
            name="Mega Knight",
            cost=4,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.BRAWLER, Traits.ACE]
        )
        
        self.troops["archer_queen"] = Troop(
            name="Archer Queen",
            cost=5,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.CLAN, Traits.AVENGER]
        )
        
        self.troops["skeleton_king"] = Troop(
            name="Skeleton King",
            cost=5,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.UNDEAD, Traits.JUGGERNAUT]
        )
        
        self.troops["golden_knight"] = Troop(
            name="Golden Knight",
            cost=5,
            stars=MergeLevel.ONE_STAR,
            traits=[Traits.NOBLE, Traits.ASSASSIN]
        )
    
    def get_troop(self, name: str) -> Optional[Troop]:
        """Get troop by name (case insensitive)"""
        # Convert name to match our internal naming (handle spaces and cases)
        normalized_name = name.lower().replace(" ", "_").replace(".", "")
        return self.troops.get(normalized_name)
    
    def get_troops_by_cost(self, cost: int) -> List[Troop]:
        """Get all troops with specific elixir cost"""
        return [troop for troop in self.troops.values() if troop.cost == cost]
    
    def get_troops_by_merge_level(self, merge_level: MergeLevel) -> List[Troop]:
        """Get all troops of specific merge level"""
        return [troop for troop in self.troops.values() if troop.stars == merge_level]
    
    def upgrade_troop_stars(self, troop_name: str, new_stars: MergeLevel) -> Optional[Troop]:
        """Upgrade a troop to a new merge level (returns new troop instance)"""
        base_troop = self.get_troop(troop_name)
        if not base_troop:
            return None
        
        # Create upgraded troop with new merge level
        upgraded_troop = Troop(
            name=base_troop.name,
            cost=base_troop.cost,
            stars=new_stars,
            traits=base_troop.traits.copy()  # Keep same traits
        )
        
        return upgraded_troop
    
    def get_troops_with_trait(self, trait: Traits) -> List[Troop]:
        """Get all troops with specific trait"""
        return [troop for troop in self.troops.values() if trait in troop.traits]
    
    def get_all_troops(self) -> List[Troop]:
        """Get all troops sorted by cost"""
        return sorted(self.troops.values(), key=lambda t: (t.cost, t.name))
    
    def print_summary(self):
        """Print a summary of all troops"""
        print("=== TROOP REGISTRY SUMMARY (Merge Tactics) ===")
        print(f"Total troops: {len(self.troops)}")
        
        for merge_level in MergeLevel:
            troops = self.get_troops_by_merge_level(merge_level)
            print(f"\n{merge_level.name} ({merge_level.value}⭐): {len(troops)} troops")
            for troop in sorted(troops, key=lambda t: t.cost):
                traits_str = ", ".join([trait.name for trait in troop.traits[:3]])  # Show first 3 traits
                if len(troop.traits) > 3:
                    traits_str += "..."
                print(f"  {troop.name:15} | {troop.cost} elixir | {traits_str}")

# Global registry instance
TROOP_REGISTRY = TroopRegistry()

def get_troop_by_icon_name(icon_name: str) -> Optional[Troop]:
    """Helper function to get troop from icon detection"""
    return TROOP_REGISTRY.get_troop(icon_name)

def get_troops_with_trait_name(trait_name: str) -> List[Troop]:
    """Helper function to get troops by trait name (string)"""
    try:
        trait_enum = Traits[trait_name.upper()]
        return TROOP_REGISTRY.get_troops_with_trait(trait_enum)
    except KeyError:
        return []

# Example usage functions
if __name__ == "__main__":
    # Print full summary
    TROOP_REGISTRY.print_summary()
    
    print("\n=== EXAMPLE QUERIES ===")
    
    # Example: Get specific troop
    pekka = TROOP_REGISTRY.get_troop("pekka")
    print(f"P.E.K.K.A: {pekka}")
    
    # Example: Get all 3-cost troops
    three_cost = TROOP_REGISTRY.get_troops_by_cost(3)
    print(f"\n3-cost troops: {[t.name for t in three_cost]}")
    
    # Example: Get all troops with RANGER trait
    rangers = TROOP_REGISTRY.get_troops_with_trait(Traits.RANGER)
    print(f"\nRANGER troops: {[t.name for t in rangers]}")
    
    # Example: Get all troops with GOBLIN trait
    goblins = TROOP_REGISTRY.get_troops_with_trait(Traits.GOBLIN)
    print(f"\nGOBLIN troops: {[t.name for t in goblins]}")
    
    # Example: Get all 1-star troops (base merge level)
    one_star = TROOP_REGISTRY.get_troops_by_merge_level(MergeLevel.ONE_STAR)
    print(f"\n1-star troops: {[t.name for t in one_star]}")
