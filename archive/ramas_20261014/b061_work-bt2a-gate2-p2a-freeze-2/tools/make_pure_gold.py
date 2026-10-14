import re

src = r"C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\HFTImpulseZones_Gold.cs"
dst = r"C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\HFTImpulseZones_Gold_Pure.cs"

with open(src, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Truncate any auto-generated code at the end
if "#region NinjaScript generated code" in text:
    text = text.split("#region NinjaScript generated code")[0].strip() + "\n"

# 2. Rename class and indicator Name
text = text.replace("public class HFTImpulseZones_Gold : Indicator", "public class HFTImpulseZones_Gold_Pure : Indicator")
text = text.replace('Name = "HFTImpulseZones_Gold";', 'Name = "HFTImpulseZones_Gold_Pure";')
text = text.replace('ShowSimulation = true;', 'ShowSimulation = false;')
text = text.replace('ShowTradeBoxes = true;', 'ShowTradeBoxes = false;')
text = text.replace('ShowStatsOverlay = true;', 'ShowStatsOverlay = false;')
text = text.replace('ShowSignalArrows = true;', 'ShowSignalArrows = false;')

with open(dst, "w", encoding="utf-8") as f:
    f.write(text)

print("HFTImpulseZones_Gold_Pure.cs created successfully!")
