# Python2.7
'''
 A*, path planner solution


 note xml includes all nodes for all partially-present ways
 uses a bounding box to ignore nodes outside the region, should be safe
'''

from Tkinter import *
import struct
import xml.etree.ElementTree as ET
from Queue import *
import math

# bounds of the window, in lat/long
LEFTLON = -78.9035
RIGHTLON = -78.8085
TOPLAT = 43.9448
BOTLAT = 43.8765
WIDTH = RIGHTLON-LEFTLON
HEIGHT = TOPLAT-BOTLAT
# ratio of one degree of longitude to one degree of latitude 
LONRATIO = math.cos(TOPLAT*3.1415/180)
WINWID = 800
WINHGT = (int)((WINWID/LONRATIO)*HEIGHT/WIDTH)
TOXPIX = WINWID/WIDTH
TOYPIX = WINHGT/HEIGHT
#width,height of elevation array
EPIX = 3601
# approximate number of meters per degree of latitude
MPERLAT = 111000
MPERLON = MPERLAT*LONRATIO

def node_dist(src, dest):
    ''' Euclidean distance between the source and goal node, in meters. '''
    dx = (dest.pos[0]-src.pos[0])*MPERLON
    dy = (dest.pos[1]-src.pos[1])*MPERLAT
    return math.sqrt(dx**2 + dy**2)

def elev_cost(src, dest):
    ''' 
    If there is an increase in elevation, calculate cost.

    The cost is the difference in elevation which is squared in order to increase
    its contribution to the overall cost.

    Since this is meant for walking, climbing a hill is physically expensive and walking downhill
    is considered free.
    '''
    cost = 0
    if dest.elev > src.elev:
            # change in elevation squared to place higher importance on
            cost = (dest.elev-src.elev)**2

    return cost

class Node():
    ''' Graph (map) node, not a search node! '''
    __slots__ = ('id', 'pos', 'ways', 'elev')
    def __init__(self,id,p,e=0):
        self.id = id
        self.pos = p
        self.ways = []
        self.elev = e
        self.waystr = None
    def __str__(self):
        if self.waystr is None:
            self.waystr = self.get_waystr()
        return str(self.pos) + ": " + self.waystr
    def get_waystr(self):
        if self.waystr is None:
            self.waystr = ""
            self.wayset = set()
            for w in self.ways:
                self.wayset.add(w.way.name)
            for w in self.wayset:
                self.waystr += w.encode("utf-8") + " "
        return self.waystr
        

class Edge():
    ''' Graph (map) edge. Includes cost computation.'''
    __slots__ = ('way','dest')
    def __init__(self, w, src, d):
        self.way = w
        self.dest = d
        self.cost = node_dist(src,d) #euclidean distance between nodes
        self.cost += elev_cost(src,d) #elevation difference between nodes

class Way():
    ''' A way is an entire street, for drawing, not searching. '''
    __slots__ = ('name','type','nodes')
    # nodes here for ease of drawing only
    def __init__(self,n,t):
        self.name = n
        self.type = t
        self.nodes = []

class Planner():
    __slots__ = ('nodes', 'ways')
    def __init__(self,n,w):
        self.nodes = n
        self.ways = w

    def heur(self,node,gnode):
        '''
        Heuristic function is a combination of euclidean distance and change in elevation.

        Euclidean distance gives the most direct path to the goal node, which will always be equal or lesser than
        the actual cost.

        Similiarly, the elevation distance is the absolute minimum elevation required to reach the goal node, meaning
        it will always be equal or lesser than the actual cost.

        Since neither of these distances will ever over-estimate the cost, the heuristic is admissable.
        '''
        
        distCost = node_dist(node,gnode)
        elevCost = elev_cost(node,gnode)

        totalCost = distCost + elevCost

        return totalCost
    
    def plan(self,s,g):
        '''
        Standard A* search
        '''
        parents = {}
        costs = {}
        q = PriorityQueue()
        q.put((self.heur(s,g),s))
        parents[s] = None
        costs[s] = 0

        print "Heuristic predicts cost as:", self.heur(s,g)

        while not q.empty():
            cf, cnode = q.get()
            if cnode == g:
                print ("Path found, time will be", costs[g]*60/5000) #5 km/hr on flat
                print "Actual cost:", costs[g]
                return self.make_path(parents,g)
            for edge in cnode.ways:
                newcost = costs[cnode] + edge.cost
                if edge.dest not in parents or newcost < costs[edge.dest]:
                    parents[edge.dest] = (cnode, edge.way)
                    costs[edge.dest] = newcost
                    q.put((self.heur(edge.dest,g)+newcost,edge.dest))

    def make_path(self,par,g):
        nodes = []
        ways = []
        curr = g
        nodes.append(curr)
        while par[curr] is not None:
            prev, way = par[curr]
            ways.append(way.name)
            nodes.append(prev)
            curr = prev
        nodes.reverse()
        ways.reverse()
        return nodes,ways

class PlanWin(Frame):
    '''
    All the GUI pieces to draw the streets, allow places to be selected,
    and then draw the resulting path.
    '''
    
    __slots__ = ('whatis', 'nodes', 'ways', 'elevs', 'nodelab', 'elab', \
                 'planner', 'lastnode', 'startnode', 'goalnode')
    
    def lat_lon_to_pix(self,latlon):
        x = (latlon[1]-LEFTLON)*(TOXPIX)
        y = (TOPLAT-latlon[0])*(TOYPIX)
        return x,y

    def pix_to_elev(self,x,y):
        return self.lat_lon_to_elev(((TOPLAT-(y/TOYPIX)),((x/TOXPIX)+LEFTLON)))

    def lat_lon_to_elev(self,latlon):
        row = int(round((latlon[0] - int(latlon[0])) * (EPIX-1), 0))
        col = int(round((latlon[1] - int(latlon[1])) * (EPIX-1), 0))

        return self.elevs[row*EPIX+col]

    def maphover(self,event):
        self.elab.configure(text = str(self.pix_to_elev(event.x,event.y)))
        for (dx,dy) in [(0,0),(-1,0),(0,-1),(1,0),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            ckpos = (event.x+dx,event.y+dy)
            if ckpos in self.whatis:
                self.lastnode = self.whatis[ckpos]
                lnpos = self.lat_lon_to_pix(self.nodes[self.lastnode].pos)
                self.canvas.coords('lastdot',(lnpos[0]-2,lnpos[1]-2,lnpos[0]+2,lnpos[1]+2))
                nstr = str(self.lastnode)
                nstr += " "
                nstr += str(self.nodes[self.whatis[ckpos]].get_waystr())
                self.nodelab.configure(text=nstr)
                return

    def mapclick(self,event):
        ''' Canvas click handler:
        First click sets path start, second sets path goal 
        '''
        print "Clicked on "+str(event.x)+","+str(event.y)+" last node "+str(self.lastnode)

        if self.lastnode is None:
            return
        if self.startnode is None:
            self.startnode = self.nodes[self.lastnode]
            self.snpix = self.lat_lon_to_pix(self.startnode.pos)
            self.canvas.coords('startdot',(self.snpix[0]-2,self.snpix[1]-2,self.snpix[0]+2,self.snpix[1]+2))
        elif self.goalnode is None:
            self.goalnode = self.nodes[self.lastnode]
            self.snpix = self.lat_lon_to_pix(self.goalnode.pos)
            self.canvas.coords('goaldot',(self.snpix[0]-2,self.snpix[1]-2,self.snpix[0]+2,self.snpix[1]+2))

        print "Start: ", self.startnode
        print "Goal: ", self.goalnode


    def clear(self):
        ''' Clear button callback. '''
        self.lastnode = None
        self.goalnode = None
        self.startnode = None
        self.canvas.coords('startdot',(0,0,0,0))
        self.canvas.coords('goaldot',(0,0,0,0))
        self.canvas.coords('path',(0,0,0,0))
            
    def plan_path(self):
        ''' Path button callback, plans and then draws path.'''
        print "Planning!"
        if self.startnode is None or self.goalnode is None:
            print "Sorry, not enough info."
            return
        print ("From", self.startnode.id, "to", self.goalnode.id)
        nodes,ways = self.planner.plan(self.startnode, self.goalnode)
        lastway = ""
        for wayname in ways:
            if wayname != lastway:
                print wayname
                lastway = wayname
        coords = []
        for node in nodes:
            npos = self.lat_lon_to_pix(node.pos)
            coords.append(npos[0])
            coords.append(npos[1])
            #print node.id
        self.canvas.coords('path',*coords)
        
    def __init__(self,master,nodes,ways,elevs):
        self.whatis = {}
        self.nodes = nodes
        self.ways = ways
        self.elevs = elevs
        self.startnode = None
        self.goalnode = None
        self.lastnode = None
        self.planner = Planner(nodes,ways)
        thewin = Frame(master)
        w = Canvas(thewin, width=WINWID, height=WINHGT, cursor="crosshair")
        w.bind("<Button-1>", self.mapclick)
        w.bind("<Motion>", self.maphover)
        for waynum in self.ways:
            nlist = self.ways[waynum].nodes
            thispix = self.lat_lon_to_pix(self.nodes[nlist[0]].pos)
            if len(self.nodes[nlist[0]].ways) > 2:
                self.whatis[((int)(thispix[0]),(int)(thispix[1]))] = nlist[0]
            for n in range(len(nlist)-1):
                nextpix = self.lat_lon_to_pix(self.nodes[nlist[n+1]].pos)
                self.whatis[((int)(nextpix[0]),(int)(nextpix[1]))] = nlist[n+1]
                w.create_line(thispix[0],thispix[1],nextpix[0],nextpix[1])
                thispix = nextpix


        #print(self.whatis)
        #w.create_rectangle(0, 0, 40, 40, fill='red')
        # other visible things are hiding for now...
        w.create_line(0,0,0,0,fill='orange',width=3,tag='path')

        w.create_oval(0,0,0,0,outline='green',fill='green',tag='startdot')
        w.create_oval(0,0,0,0,outline='red',fill='red',tag='goaldot')
        w.create_oval(0,0,0,0,outline='blue',fill='blue',tag='lastdot')
        w.pack(fill=BOTH)
        self.canvas = w

        cb = Button(thewin, text="Clear", command=self.clear)
        cb.pack(side=RIGHT,pady=5)

        sb = Button(thewin, text="Plan!", command=self.plan_path)
        sb.pack(side=RIGHT,pady=5)

        nodelablab = Label(thewin, text="Node:")
        nodelablab.pack(side=LEFT, padx = 5)
        
        self.nodelab = Label(thewin,text="None")
        self.nodelab.pack(side=LEFT,padx = 5)

        elablab = Label(thewin, text="Elev:")
        elablab.pack(side=LEFT, padx = 5)

        self.elab = Label(thewin, text = "0")
        self.elab.pack(side=LEFT, padx = 5)
        
        thewin.pack()


def build_elevs(efilename):
    ''' read in elevations from a file. '''
    efile = open(efilename)
    estr = efile.read()
    elevs = []
    for spot in range(0,len(estr),2):
        # .bil hgt is little endian
        elevs.append(struct.unpack('<h',estr[spot:spot+2])[0])

    return elevs

def build_graph(elevs):
    ''' Build the search graph from the OpenStreetMap XML. '''
    tree = ET.parse('map.osm')
    root = tree.getroot()

    nodes = dict()
    ways = dict()
    waytypes = set()
    for item in root:
        if item.tag == 'node':
            coords = ((float)(item.get('lat')),(float)(item.get('lon')))
            erow = int(round((coords[0] - int(coords[0])) * (EPIX-1), 0))
            ecol = int(round((coords[1] - int(coords[1])) * (EPIX-1), 0))
            try:
                el = elevs[erow*EPIX+ecol]
            except IndexError:
                el = 0
            nodes[(long)(item.get('id'))] = Node((long)(item.get('id')),coords,el)            
        elif item.tag == 'way':
            useme = False
            oneway = False
            myname = 'unnamed way'
            for thing in item:
                if thing.tag == 'tag' and thing.get('k') == 'highway':
                    useme = True
                    mytype = thing.get('v')
                if thing.tag == 'tag' and thing.get('k') == 'name':
                    myname = thing.get('v')
                if thing.tag == 'tag' and thing.get('k') == 'oneway':
                    if thing.get('v') == 'yes':
                        oneway = True
            if useme:
                wayid = (long)(item.get('id'))
                ways[wayid] = Way(myname,mytype)
                nlist = []
                for thing in item:
                    if thing.tag == 'nd':
                        nlist.append((long)(thing.get('ref')))
                thisn = nlist[0]
                for n in range(len(nlist)-1):
                    nextn = nlist[n+1]
                    nodes[thisn].ways.append(Edge(ways[wayid],nodes[thisn],nodes[nextn]))
                    thisn = nextn
                if not oneway:
                    thisn = nlist[-1]
                    for n in range(len(nlist)-2,-1,-1):
                        nextn = nlist[n]
                        nodes[thisn].ways.append(Edge(ways[wayid],nodes[thisn],nodes[nextn]))
                        thisn = nextn                
                ways[wayid].nodes = nlist
    return nodes, ways

elevs = build_elevs("n43w079.bil")
nodes, ways = build_graph(elevs)

master = Tk()
thewin = PlanWin(master,nodes,ways,elevs)

mainloop()

