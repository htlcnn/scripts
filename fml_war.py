#!/usr/bin/env python3
'''
Simulate a battle between 2 characters with random weapons
Weapon info got from CS: GO
This is a solution for an OOP exercise at PyFML
'''
import random
import pandas as pd


class Character(object):
    def __init__(self, name, health, weapon):
        self.name = name
        self.health = health
        self.weapon = weapon
        
    def fight(self, character):
        character.health -= self.weapon.damage
        
    def __str__(self):
        return '{}, Weapon: {}, Health: {}'.format(self.name, self.weapon.name, self.health)
    
class Weapon(object):
    def __init__(self, name, damage):
        self.name = name
        self.damage = damage
    def __str__(self):
        return '{}, {} dam'.format(self.name, self.damage)
    
def get_random_weapon():
    df = pd.read_html('http://strike-counter.com/cs-go-stats/weapons-data')
    weapon_data = df[0]
    weapon_name = random.choice(weapon_data['Name'])
    weapon_damage = weapon_data[weapon_data['Name'] == weapon_name]['Damage'].values[0]
    return Weapon(weapon_name, weapon_damage)

def battle(a, b):
    turns = 0
    while a.health > 0 and b.health > 0:
        turns += 1
        print('{:*^79}'.format('Turn ' + str(turns)))
        a.fight(b)
        print('{} hit {} with {}'.format(a.name, b.name, a.weapon))

        if b.health < 0:
            winner = a
            b.health = 0
            print(a)
            print(b)
            print('{} dead after {} turns'.format(b.name, turns))
            print('Winner: {}'.format(a))
        else:
            b.fight(a)
            print('{} hit {} with {}'.format(b.name, a.name, b.weapon))
            if a.health < 0:
                a.health = 0
                print(a)
                print(b)
                print('{} dead after {} turns'.format(a.name, turns))
                print('Winner: {}'.format(b))

def main():
    char1 = Character('htl', 100, get_random_weapon())
    char2 = Character('hvn', 100, get_random_weapon())
    battle(char1, char2)
    
if __name__ == '__main__':
    main()