--------------------------------------------------------------
-- This file contains a LUCCME APPLICATION MODEL definition --
--               Compatible with LuccME 3.0                 --
--        Generated with LuccMe Model Configurator          --
--               11/05/2017 at 16:32:03                     --
--------------------------------------------------------------

--------------------------------------------------------------
-- Creating Terraview Project                               --
--------------------------------------------------------------

import("gis")

local projFile = File("t3mp.tview")
if(projFile:exists()) then
	projFile:delete()
end

proj = Project {
	file = "t3mp.tview",
	clean = true
}

l1 = Layer{
	project = proj,
	name = "layer",
	file = "../data/cs_moju/cs_moju.shp"
}

--------------------------------------------------------------
-- LuccME Model                                             --
--------------------------------------------------------------

import("luccme")

dofile("lab6_submodel.lua")


--------------------------------------------------------------
-- LuccME APPLICATION MODEL DEFINITION                      --
--------------------------------------------------------------
Lab6 = LuccMEModel
{
	name = "Lab6",

	-----------------------------------------------------
	-- Temporal dimension definition                   --
	-----------------------------------------------------
	startTime = 1999,
	endTime = 2004,

	-----------------------------------------------------
	-- Spatial dimension definition                    --
	-----------------------------------------------------
	cs = CellularSpace
	{
		project = "t3mp.tview",
		layer = "layer",
		cellArea = 1,
	},

	-----------------------------------------------------
	-- Land use variables definition                   --
	-----------------------------------------------------
	landUseTypes =
	{
		"f", "d", "o"
	},

	landUseNoData = "o",

	-----------------------------------------------------
	-- Behaviour dimension definition:                 --
	-- DEMAND, POTENTIAL AND ALLOCATION COMPONENTS     --
	-----------------------------------------------------
	demand = D1,
	potential = P1,
	allocation = A1,

	save  =
	{
		outputTheme = "Lab6_",
		mode = "multiple",
		saveYears = {2004},
		saveAttrs = 
		{
			"d_out",
		},

	},

	isCoupled = false
}  -- END LuccME application model definition

-----------------------------------------------------
-- ENVIROMMENT DEFINITION                          --
-----------------------------------------------------
timer = Timer
{
	Event
	{
		start = Lab6.startTime,
		action = function(event)
					Lab6:run(event)
				  end
	}
}

env_Lab6 = Environment{}
env_Lab6:add(timer)

-----------------------------------------------------
-- ENVIROMMENT EXECUTION                           --
-----------------------------------------------------
if Lab6.isCoupled == false then
	tsave = databaseSave(Lab6)
	env_Lab6:add(tsave)
	env_Lab6:run(Lab6.endTime)
	saveSingleTheme (Lab6, true)
	projFile = File("t3mp.tview")
	if(projFile:exists()) then
		projFile:delete()
	end
end
