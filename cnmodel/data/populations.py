# -*- encoding: utf-8 -*-
from ._db import add_table_data

add_table_data('populations', row_key='field', col_key='cell_type', 
               species='mouse', data=u"""

----------------------------------------------------------------------------------------------------------
           ihc        sgc        bushy      tstellate    dstellate     octopus     pyramidal   tuberculoventral
                                                                                                
n_cells    725 [4]    9780  [1]  6500 [2]   6500 [2]     650 [3]       5000        3000        5000   
cf_min     2000       2000       2000       2000         2000          2000        2000        2000   
cf_max     90000      90000      90000      90000        90000         90000       90000       90000
----------------------------------------------------------------------------------------------------------

[1] Ehret, G. Quantative analysis of Nerve fiber Densities in the cohclear of the House Mouse (Mus musculus)
    J. Comp. Neurol. 183: 73-88, 1979.
    Total number of fibers 12578; IHC: 9780, OHC only = 703, Efferents 1867
    NMRI mice 4-10 weeks old.
    For future reference, Ehret cites Gacek and Rasmussen 1961 for total numbers in guinea pig and cat.

[2] Rough estimate from allen brain atlas data:
    Volume of VCN is 0.377 mm^3, by counting voxels with 'VCO' (101) label in Common Coordinate Framework atlas.
        753370 voxels * 0.5 * 10e-6**3 m^3/vox = 0.377 mm^3
    Counted Slc17a7 (pan-excitatory) cell bodies in a 500x500 um chunk of VCN
        http://mouse.brain-map.org/experiment/siv?id=69014470&imageId=68856767&initImage=ish&coordSystem=pixel&x=7616.5&y=4144.5&z=1
        266 cells in 500x500 um = 34707 cells / mm^2
        34707**3/2 * 0.377 mm^3 = 13084 cells total
        Assume half are bushy, half are T-stellate
        
[3] Rough estimate from allen brain atlas data:
    Similar to [2], using Gad1 inhibitory marker
    http://mouse.brain-map.org/experiment/siv?id=75492764&imageId=75405134&initImage=ish&coordSystem=pixel&x=5320.5&y=3232.5&z=1
    36 cells in 500x500 um = 144e6 / m^2  ~= 1728 / mm^2
    = 651 cells total  (VCN, unilateral)

[4] Data from:
    Ding, D., McFadden, S.L. and Salvi, R. Willot "Cochlear Hair Cell Densities and Inner-Ear Staining
    Techniques" in : Willot, J.F. Ed. "Handbook of Mouse Auditory Research". CRC Press, 2001. 
    Table 13.6 (p192), CBA = 725  (other strains in similar range)
    
    A similar number comes from Ehret, G. and Frankenreiter, M. "Quantitative Analysis of Cochlear Structures
    in the House Mouse in Relation to Mechanisms of Acoustical Information Processing". J. Comp. Physiol. A.
    122: 65-85, 1977.
    NMRI strain, 6-8 weeks old: IHC count = 765.
""")


