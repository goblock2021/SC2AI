"""
SC2AI - By GoBlock2021
代码参照以下文档编写https://github.com/ClausewitzCPU0/SC2AI
"""

import random
import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Human, Bot, Computer
from sc2.constants import *
from sc2.ids.buff_id import BuffId


class SentdeBot(sc2.BotAI):
    global gamestep
    global againstAI

    async def on_step(self, iteration: int):
        await self.distribute_workers()  # distribute_workers是内置方法，代表自动让农民采矿
        await self.game_timer()
        await self.nexus_work()
        await self.build_pylons()
        await self.build_assimilators()
        await self.expand()
        await self.offensive_force_buildings()
        await self.build_offensive_force()
        await self.attack()
        await self.getvision()

    # TODO: 加一个游戏时期的判断
    async def game_timer(self):
        pass

    async def nexus_work(self):
        """
        造农民
        """
        for nexus in self.units(NEXUS).ready.idle:
            if self.can_afford(PROBE):
                if self.units(PROBE).amount < self.units(NEXUS).amount * 16:
                    await self.do(nexus.train(PROBE))

        # Nexus 将在必要时使用技能
        for nexus in self.units(NEXUS):
            if len(self.units().enemy.closer_than(30, nexus)) > 0:
                if self.units(CHANGELINGMARINESHIELD).closer_than(8, nexus).amount > 0:
                    await self.do(nexus(AbilityId.NEXUSSHIELDOVERCHARGE_NEXUSSHIELDOVERCHARGE, self.units(CHANGELINGMARINESHIELD).closer_than(8, nexus).first))
            # 如果水晶的电量充足且附近没有敌人
            elif nexus.energy_percentage > 0.6:
                # 如果工人不够但是在造工人就加速自己
                if self.workers.amount < self.units(NEXUS).amount * 16 * 0.8 and not nexus.is_idle:
                    await self.do(nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus))
                # 否则加速附件造兵建筑
                # 第一个考虑 Star Gate
                elif self.units(STARGATE).closer_than(8, nexus).amount > 0 and not self.units(STARGATE).closer_than(8, nexus).first.is_idle:
                    await self.do(nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, self.units(STARGATE).closer_than(8, nexus).first))
                # 然后考虑加速 Gate Way
                elif self.units(GATEWAY).closer_than(8, nexus).amount > 0 and not self.units(GATEWAY).closer_than(8, nexus).first.is_idle:
                    await self.do(nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, self.units(GATEWAY).closer_than(8, nexus).first))
                # 实在找不到造兵建筑且自己要造东西就加速自己
                elif not nexus.is_idle:
                    await self.do(nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus))



    async def build_pylons(self):
        """
        人口空余不足20时造水晶。
        """
        if self.supply_left < 20 and self.already_pending(PYLON) < 2:
            if self.units(NEXUS).exists:
                if self.can_afford(PYLON):
                    min_pylon_count = -1
                    for one_nexus in self.units(NEXUS):
                        found = len(self.units(PYLON).closer_than(5, one_nexus))
                        if min_pylon_count == -1:
                            min_pylon_count = found
                            found_nexus = one_nexus

                        if found < min_pylon_count:
                            min_pylon_count = found
                            found_nexus = one_nexus

                    await self.build(PYLON, near=found_nexus, max_distance=5)  # near表示建造地点。后期可以用深度学习优化

    async def build_assimilators(self):
        """
        建造气矿
        """
        for nexus in self.units(NEXUS).ready:
            vespenes = self.state.vespene_geyser.closer_than(25.0, nexus)
            for vespene in vespenes:
                if not self.can_afford(ASSIMILATOR):
                    break
                worker = self.select_build_worker(vespene.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1.0, vespene).exists:
                    await self.do(worker.build(ASSIMILATOR, vespene))

    async def expand(self):
        # 无论如何基地少于3个就造
        if self.units(NEXUS).amount < 4 and self.can_afford(NEXUS):
            await self.expand_now()
        # 如果没看到敌人就造家
        elif self.minerals >= 5000 and self.units(NEXUS).amount < 10:
            danger = False
            for one_nexus in self.units(NEXUS):
                if len(self.units().enemy.closer_than(30, one_nexus)) > 0:
                    danger = True
                    break
            if not danger:
                await self.expand_now()

    async def offensive_force_buildings(self):
        """
        建造产兵建筑（将要弃用）
        """
        if self.units(PYLON).ready.exists:
            pylon = self.units(PYLON).ready.random
            if self.units(GATEWAY).ready.exists:
                if not self.units(CYBERNETICSCORE).ready.exists:
                    if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                        await self.build(CYBERNETICSCORE, near=pylon)
            # 造 Gate Way 准备造兵
            if self.units(GATEWAY).amount < 2:
                if self.can_afford(GATEWAY):
                    await self.build(GATEWAY, near=pylon)
            elif self.units(GATEWAY).amount < self.units(NEXUS).amount * 3:
                if self.units(GATEWAY).amount < self.units(NEXUS).amount and self.minerals >= 1200:
                    await self.build(GATEWAY, near=pylon)
                elif self.units(GATEWAY).amount < self.units(NEXUS).amount * 1.5 and self.minerals >= 3000:
                    await self.build(GATEWAY, near=pylon)
            # 先赶紧造一个 Star Gate
            if self.units(STARGATE).amount == 0:
                if self.can_afford(STARGATE):
                    await self.build(STARGATE, near=pylon)
            # 如果没造 Fleet Beacon 就赶紧造
            elif not self.units(FLEETBEACON).exists and not self.already_pending(FLEETBEACON):
                if self.can_afford(FLEETBEACON):
                    await self.build(FLEETBEACON, near=pylon)
            # 安心多造一点 Star Gate
            elif self.units(STARGATE).amount < self.units(NEXUS).amount * 3:
                if self.units(STARGATE).amount < self.units(NEXUS).amount and self.minerals >= 1500:
                    await self.build(GATEWAY, near=pylon)
                elif self.units(STARGATE).amount < self.units(NEXUS).amount * 1.5 and self.minerals >= 4000:
                    await self.build(GATEWAY, near=pylon)
                elif self.minerals >= 10000:
                    await self.build(GATEWAY, near=pylon)

    # TODO:火速做一个新的分布式造兵的方案
    async def offensive_force_buildings_new(self):
        for nexus in self.units(NEXUS):
            pass

    async def build_offensive_force(self):  # TODO:多造点不同的兵种
        """
        建造战斗单位
        """
        for gw in self.units(GATEWAY).ready.noqueue:
            if self.can_afford(STALKER) and self.supply_left >= 2 and self.units(STALKER).amount <= 50:
                await self.do(gw.train(STALKER))

        if self.units(STARGATE).exists and self.units(FLEETBEACON).exists:

            for gw in self.units(GATEWAY).ready.noqueue:
                if self.can_afford(STALKER) and self.supply_left >= 30:
                    await self.do(gw.train(random.choice([VOIDRAY,CARRIER])))


    def find_target(self, state):  # TODO:众神之父赐予我视野! 解决一下把对面家拆了就抓瞎的BUG
        """
        寻找敌方单位
        注意这个函数不是异步的，不用加async
        """
        if len(self.known_enemy_units) > 0:
            return random.choice(self.known_enemy_units)
        elif len(self.known_enemy_structures) > 0:
            return random.choice(self.known_enemy_structures)
        else:
            return self.enemy_start_locations[0]

    async def attack(self):
        """
        控制追猎攻击视野内敌方单位
        """
        if self.units(STALKER).amount > 30:  # 追猎数量够多时主动出击
            for s in self.units(STALKER).idle:
                await self.do(s.attack(self.find_target(self.state)))

        if self.units(STALKER).amount > 5:
            if len(self.known_enemy_units) > 0:
                for s in self.units(STALKER).idle:
                    await self.do(s.attack(random.choice(self.known_enemy_units)))

    async def getvision(self):
        """
        想办法用探机随机游走
        """
        pass


def main():
    race_type = ("t")
    if race_type == "h":
        run_game(maps.get("AutomatonLE"), [
            Human(Race.Protoss),
            Bot(Race.Protoss, SentdeBot())], realtime=True)  # realtime设为False可以加速
    else:
        run_game(maps.get("AutomatonLE"), [
            Bot(Race.Protoss, SentdeBot()),
            Computer(Race.Protoss, Difficulty.Medium)], realtime=False)  # realtime设为False可以加速


if __name__ == '__main__':
    main()
