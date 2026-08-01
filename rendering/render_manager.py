"""
botyaraRTS - rendering/render_manager.py
Менеджер рендеринга — связывает все рендеры и выбирает нужный для каждой сущности.
"""
import pygame
from rendering.terrain_renderer import TerrainRenderer
from rendering.infantry_renderer import InfantryRenderer
from rendering.vehicle_renderer import VehicleRenderer
from rendering.aircraft_renderer import AircraftRenderer
from rendering.special_renderer import SpecialRenderer
from rendering.building_renderer import BuildingRenderer
from rendering.projectile_renderer import ProjectileRenderer
from rendering.unit_renderer import UnitRenderer


class RenderManager:
    """Центральный менеджер визуализации."""

    def __init__(self, tilemap):
        self.terrain = TerrainRenderer(tilemap)
        self.anim_time = 0

        # Маппинг класс → рендер-функция
        self._unit_renderers = {}
        self._setup_renderers()

    def _setup_renderers(self):
        """Настройка маппинга юнитов на рендер-функции."""
        from entities.worker import Worker
        from entities.infantry import (Scout, Trooper, Sniper,
                                        RocketSoldier, Medic, ExoSoldier)
        from entities.vehicles import (Buggy, Tank, Flamethrower,
                                        SiegeTank, MobileAA, MechWalker)
        from entities.aircraft import (ScoutDrone, AttackHelicopter,
                                        Fighter, Bomber, Transport)
        from entities.special_units import (Saboteur, PsiUnit,
                                             MineDrone, SuperUnit)

        self._unit_renderers = {
            Worker: InfantryRenderer.render_worker,
            Scout: InfantryRenderer.render_scout,
            Trooper: InfantryRenderer.render_trooper,
            Sniper: InfantryRenderer.render_sniper,
            RocketSoldier: InfantryRenderer.render_rocket_soldier,
            Medic: InfantryRenderer.render_medic,
            ExoSoldier: InfantryRenderer.render_exo_soldier,
            Buggy: VehicleRenderer.render_buggy,
            Tank: VehicleRenderer.render_tank,
            Flamethrower: VehicleRenderer.render_flamethrower,
            SiegeTank: VehicleRenderer.render_siege_tank,
            MobileAA: VehicleRenderer.render_mobile_aa,
            MechWalker: VehicleRenderer.render_mech_walker,
            ScoutDrone: AircraftRenderer.render_scout_drone,
            AttackHelicopter: AircraftRenderer.render_attack_helicopter,
            Fighter: AircraftRenderer.render_fighter,
            Bomber: AircraftRenderer.render_bomber,
            Transport: AircraftRenderer.render_transport,
            Saboteur: SpecialRenderer.render_saboteur,
            PsiUnit: SpecialRenderer.render_psi_unit,
            MineDrone: SpecialRenderer.render_mine_drone,
            SuperUnit: SpecialRenderer.render_super_unit,
        }

    def update(self, dt):
        """Обновление анимации."""
        self.anim_time += dt
        self.terrain.update(dt)

    def render_terrain(self, surface, camera):
        """Отрисовка ландшафта."""
        self.terrain.render(surface, camera)

    def render_grid(self, surface, camera):
        """Отрисовка сетки."""
        self.terrain.render_grid(surface, camera)

    def render_entity(self, surface, camera, entity):
        """Отрисовка любой сущности (юнит или здание)."""
        if not entity.visible and not entity.selected:
            return

        if entity.is_building:
            BuildingRenderer.render_building(surface, camera, entity, self.anim_time)
        elif entity.is_unit:
            renderer = self._unit_renderers.get(type(entity))
            if renderer:
                renderer(surface, camera, entity, self.anim_time)
            else:
                # Фолбэк — базовый рендер
                entity.render(surface, camera)

        # HP bar (если не рисуется внутри рендера)
        if entity.is_unit and entity.alive:
            hp_mode = 'damaged'
            try:
                from settings import game_settings
                hp_mode = game_settings.get('hp_bar_mode')
            except Exception:
                pass

    def render_combat_effects(self, surface, camera, combat_system, local_player_id):
        """Отрисовка боевых эффектов."""
        for proj in combat_system.projectiles:
            ProjectileRenderer.render_projectile(surface, camera, proj, self.anim_time)

        for mine in combat_system.mines:
            is_owner = mine.owner_id == local_player_id
            ProjectileRenderer.render_mine(surface, camera, mine, self.anim_time, is_owner)

        for effect in combat_system.delayed_effects:
            ProjectileRenderer.render_delayed_effect(surface, camera, effect, self.anim_time)

        for text in combat_system.floating_texts:
            ProjectileRenderer.render_floating_text(surface, camera, text, self.anim_time)

    def render_death(self, surface, camera, entity):
        """Отрисовка трупа/обломков."""
        if entity.alive:
            return True

        if entity.death_timer > entity.death_duration:
            return False

        alpha = 1.0 - (entity.death_timer / entity.death_duration)
        sr = entity.get_screen_rect(camera)

        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return True

        # Обломки — затухающий серый силуэт с искрами
        death_surf = pygame.Surface((sr.width + 4, sr.height + 4), pygame.SRCALPHA)

        gray = int(60 * alpha)
        if gray > 0:
            body_color = (gray, gray // 2, gray // 3, int(200 * alpha))
            pygame.draw.rect(death_surf, body_color, (2, 2, sr.width, sr.height),
                             border_radius=2)

            # Искры (в начале)
            if alpha > 0.5:
                import random
                spark_count = int(3 * alpha)
                for _ in range(spark_count):
                    spark_x = random.randint(2, sr.width)
                    spark_y = random.randint(2, sr.height)
                    spark_color = (255, random.randint(100, 200), 0,
                                   int(200 * (alpha - 0.5) * 2))
                    pygame.draw.circle(death_surf, spark_color,
                                       (spark_x, spark_y), random.randint(1, 2))

        surface.blit(death_surf, (sr.x - 2, sr.y - 2))
        return True
