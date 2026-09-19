--------------------------------------------------------------
--       This file contains the COMPONENTS definition       --
--               Compatible with LuccME 3.0                 --
--        Generated with LuccMe Model Configurator          --
--               11/05/2017 at 16:32:03                     --
--------------------------------------------------------------

-----------------------------------------------------
-- Demand                                          --
-----------------------------------------------------
D1 = DemandPreComputedValues
{
	annualDemand =
	{
		-- "f", "d", "o"
		{5706, 205, 3}, 	-- 1999
		{5658, 253, 3}, 	-- 2000
		{5611, 300, 3}, 	-- 2001
		{5563, 348, 3}, 	-- 2002
		{5516, 395, 3}, 	-- 2003
		{5468, 443, 3} 	-- 2004
	}
}

-----------------------------------------------------
-- Potential                                       --
-----------------------------------------------------
P1 = PotentialDLogisticRegression
{
	potentialData =
	{
		-- Region 1
		{
			-- f
			{
				const = -2.34187976925989,
				elasticity = 0.0,

				betas =
				{
					media_decl = -0.0272710076327129,
					dist_area_ = 4.30977432375496,
					dist_br = 3.10319957497883,
					dist_curua = 0.445414024051873,
					dist_rios_ = 47.3556329553235,
					dist_estra = 38.4966894254506
				}
			},

			-- d
			{
				const = -0.100351497277102,
				elasticity = 0.6,

				betas =
				{
					media_decl = 0.0581358851690861,
					dist_area_ = -0.974998890251365,
					dist_br = -2.51650696123426,
					dist_curua = -1.26742746441679,
					dist_rios_ = -40.3646901047482,
					dist_estra = -23.0841140199094
				}
			},

			-- o
			{
				const = 0.01,
				elasticity = 0.5,

				betas =
				{
					
				}
			}
		}
	}
}

-----------------------------------------------------
-- Allocation                                      --
-----------------------------------------------------
A1 = AllocationDClueSLike
{
	maxIteration = 1000,
	factorIteration = 0.0001,
	maxDifference = 10,
	transitionMatrix =
	{
		--Region 1
		{
			{1, 1, 0},
			{0, 1, 0},
			{0, 0, 1}
		}
	}
}

