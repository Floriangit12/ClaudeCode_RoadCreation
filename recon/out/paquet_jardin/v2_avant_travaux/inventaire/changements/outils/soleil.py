"""Position du soleil (algorithme NOAA simplifié, précision ~0,1°) à Meylan ; table azimut / élévation par date."""
import datetime as dt
import math
import sys

LAT, LON = 45.2076, 5.7681


def soleil(t):
    """t : datetime UTC -> (azimut vrai deg depuis le nord, élévation deg)."""
    jd = t.toordinal() + 1721424.5 + (t.hour + t.minute / 60 + t.second / 3600) / 24
    n = jd - 2451545.0
    L = (280.46 + 0.9856474 * n) % 360
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    eps = math.radians(23.439 - 0.0000004 * n)
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    dec = math.asin(math.sin(eps) * math.sin(lam))
    gmst = (18.697374558 + 24.06570982441908 * n) % 24
    ha = math.radians((gmst * 15 + LON) % 360) - ra
    lat = math.radians(LAT)
    el = math.asin(math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(ha))
    az = math.atan2(-math.sin(ha), math.tan(dec) * math.cos(lat) - math.sin(lat) * math.cos(ha))
    return math.degrees(az) % 360, math.degrees(el)


if __name__ == "__main__":
    # azimut grille = azimut vrai + gamma (gamma = -2,0086 deg au site)
    for a in sys.argv[1:]:
        t = dt.datetime.fromisoformat(a)
        az, el = soleil(t)
        print(a, f"az_vrai={az:.1f} az_grille={az - 2.0086:.1f} el={el:.1f}")
