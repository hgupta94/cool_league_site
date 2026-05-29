from databases.updates.update_h2h import load_h2h
from databases.updates.update_ss import load_switcher
from databases.updates.update_matchups import load_matchups
from databases.updates.update_efficiencies import load_efficiency
from scripts.utils.constants import WEEK
from scripts.api.dataloader import DataLoader


PREVIOUS_WEEK = WEEK - 1

dataloader = DataLoader()
dataloader_week = DataLoader(week=PREVIOUS_WEEK)

load_matchups(dataloader=dataloader_week)
load_h2h(dataloader=dataloader_week)
load_switcher(dataloader=dataloader_week)
load_efficiency(dataloader=dataloader_week)
