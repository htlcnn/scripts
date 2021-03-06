#!/usr/bin/env python3
'''
check battery, if not plugged in and battery is < 15%, notify-send battery percentage
add this to /etc/crontab to check as you wish
'''
import subprocess as spr


def main():
    power = spr.check_output('upower -i /org/freedesktop/UPower/devices/line_power_AC0'.split()).decode('utf-8')
    plugged_in = [i.replace(' ', '').split(':')[1] for i in power.splitlines() if 'online' in i][0]

    batt = spr.check_output('upower -i /org/freedesktop/UPower/devices/battery_BAT0'.split()).decode('utf-8').splitlines()
    percent = [i.replace(' ', '').split(':')[1] for i in batt if 'percentage' in i][0]
    percent = int(float(percent[:-1]))
    capacity = [i.replace(' ', '').split(':')[1] for i in batt if 'capacity' in i][0]
    capacity = capacity.replace(',', '.')
    capacity = int(float(capacity[:-1]))
    real_percent = capacity * percent / 100

    if real_percent < 15 and plugged_in == 'no':
        subprocess.check_output('/usr/bin/notify-send "Battery low: {}%"'.format(real_percent), shell=True)

    print('{}%'.format(real_percent))

if __name__ == '__main__':
    main()

