'''
Join geometry walls and columns
'''
from rpw import doc, db, DB

walls = db.Collector(of_class="Wall")

with db.Transaction("Join Walls and Columns"):
    for wall in walls:
        col_on_wall = db.Collector(of_class="FamilyInstance",
                                   of_category="OST_StructuralColumns")
        bb = wall.get_BoundingBox(doc.ActiveView)
        outline = DB.Outline(bb.Min, bb.Max)
        bbfilter = DB.BoundingBoxIntersectsFilter(outline)
        col_on_wall.WherePasses(bbfilter)
        for column in col_on_wall:
            try:
                DB.JoinGeometryUtils.JoinGeometry(doc, wall, column)
            except:
                pass
