"""offline preview of the SU-76M: vehicle mesh + T-70M running-gear add-ins + ZiS-3 add-ins + a generated track"""
import sys, numpy as np, azg2, render_scene, su76_mesh as SMM
from PIL import Image
OLIVE=np.array([.42,.47,.30]); GEAR=np.array([.36,.40,.27]); STEEL=np.array([.30,.31,.29])
def scene(mesh, game='game', out='out', elevation=0.0, traverse=0.0, tex=None):
    sc=render_scene.Scene()
    sc.add_vehicle(mesh, tex if tex is not None else OLIVE, elevation=elevation, traverse=traverse,
                   addins=[(out+'/su76m_barrel.mesh.loc_def.bin','d_gun',STEEL),(out+'/su76m_breech.mesh.loc_def.bin','d_zatvor',STEEL)])
    m=azg2.read(mesh); W={n['name']:n['world'] for n in m['nodes']}
    if 'd_wheel_23' in W:
        sc._instance('%s/m_t70m_wheel.bin'%game,GEAR,W['d_wheel_23'])
    kinds={n:k for n,_,_,k in SMM.wheel_layout()}
    circles={}
    for name,kind in kinds.items():
        p=W[name][3,:3]; side=1 if p[0]>0 else -1; M=np.eye(4); M[3,:3]=p
        f={'star':'t70m_star','road':'t70m_wheel','lazy':'t70m_lazy','roller':'t70m_roller'}[kind]
        sc._instance('%s/m_%s.bin'%(game,f),GEAR,M,mirror=side>0)
        r={'star':0.30,'road':0.28,'lazy':0.28,'roller':0.135}[kind]
        circles.setdefault(side,[]).append((p[2],p[1],r,p[0]))
    for name,tpl,p,wheel in SMM.caret_layout():
        M=np.eye(4); M[3,:3]=W[name][3,:3]
        sc._instance('%s/m_%s.bin'%(game,'t70m_lcaret' if p[0]<0 else 't70m_rcaret'),GEAR,M)
    for side,cs in circles.items(): sc._track(cs,side,width=0.26,pitch=0.11,t=0.035)
    sc.add_ground(-0.875)
    return sc
VIEWS=[((-5.5,3.2,7.0),(0,0.2,0)),((5.5,3.2,7.0),(0,0.2,0)),((-5.5,3.6,-7.0),(0,0.3,0)),((2.6,1.8,3.2),(-0.2,0.8,0.3))]
def sheet(sc,path,views=VIEWS,size=(800,540)):
    ims=[sc.render(cam=c,target=t,fov=34,size=size) for c,t in views]
    W=Image.new('RGB',(size[0]*2,size[1]*((len(ims)+1)//2))); [W.paste(im,((i%2)*size[0],(i//2)*size[1])) for i,im in enumerate(ims)]; W.save(path)
if __name__=='__main__':
    sc=scene(sys.argv[1]); sheet(sc,sys.argv[2])
