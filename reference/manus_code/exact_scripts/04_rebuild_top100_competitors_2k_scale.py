import matplotlib.pyplot as plt
import numpy as np

OUT = '/home/ubuntu/work/top100_extend/top_100_keywords_competitors_original_style_jan_aug_2026.png'
months = ['Jan 26','Feb 26','Mar 26','Apr 26','May 26','Jun 26','Jul 26','Aug 26']
x = np.arange(len(months))

# New Holland and Vermeer are intentionally excluded. July/August are exact user values.
series = {
    'Virnig': {'v':[5710,5758,5263,5085,4834,3954,3765,3642], 'c':'#EF6CC1'},
    'Diamond Mower': {'v':[5060,5112,4595,4288,4340,3835,3822,3523], 'c':'#FD7804'},
    'FAE Group': {'v':[3089,3234,3096,3027,3153,3153,3020,3377], 'c':'#0A9C08'},
    'Fecon': {'v':[3369,3534,3260,3120,3190,2876,2769,2546], 'c':'#DE061D'},
    'Loftness': {'v':[1217,1339,1274,1181,1049,946,880,780], 'c':'#C4C4C4'},
    'Prinoth': {'v':[155,125,133,114,100,111,114,102], 'c':'#12BECA'},
    'Denis Cimaf': {'v':[28,24,31,20,25,91,26,22], 'c':'#F9B570'},
    'Shearex': {'v':[92,88,81,76,72,71,85,66], 'c':'#915348'},
    'Mastodon': {'v':[122,102,102,102,119,68,79,85], 'c':'#FCB4D0'},
}

plt.rcParams.update({'font.family':'Liberation Sans','font.size':15})
fig, ax = plt.subplots(figsize=(27.27,10.87), dpi=100, facecolor='white')
fig.subplots_adjust(left=0.035, right=0.985, top=0.975, bottom=0.105)
ax.set_facecolor('white')

# Requested axis change only: 2K increments, focused on the remaining competitors.
ax.set_ylim(0, 6400)
ax.set_xlim(-0.48, 7.48)
ax.set_yticks([0,2000,4000,6000])
ax.set_yticklabels(['0K','2K','4K','6K'], color='#737373', fontsize=18)
ax.set_xticks(x)
ax.set_xticklabels(months, color='#737373', fontsize=18)
ax.tick_params(axis='both', length=0, pad=14)
ax.grid(axis='y', color='#F3F3F3', linewidth=1.2)
ax.grid(axis='x', visible=False)
for spine in ax.spines.values(): spine.set_visible(False)

# Same thin colored lines, round markers, and source palette.
order=['Loftness','Prinoth','Denis Cimaf','Shearex','Mastodon','FAE Group','Fecon','Diamond Mower','Virnig']
for name in order:
    s=series[name]
    ax.plot(x,s['v'],color=s['c'],linewidth=3.2,marker='o',markersize=5.5,
            markeredgewidth=0,solid_capstyle='round',zorder=3)

# Restore the source chart's colored callout boxes and thin gray leader lines—no legend.
callouts = {
    'Diamond Mower': ((0.58,5060),(0.58,5750)),
    'Virnig': ((0.30,5710),(0.30,5200)),
    'FAE Group': ((0.86,3089),(0.86,4650)),
    'Fecon': ((1.02,3369),(1.02,4050)),
    'Loftness': ((1.72,1339),(1.72,3000)),
    'Mastodon': ((2.24,102),(2.24,2300)),
    'Prinoth': ((2.70,133),(2.70,760)),
    'Denis Cimaf': ((0.98,28),(0.98,520)),
    'Shearex': ((3.12,76),(3.12,350)),
}
for name,(anchor,labelpos) in callouts.items():
    ax.annotate(name, xy=anchor, xytext=labelpos, ha='center', va='center',
                fontsize=18, color=series[name]['c'], zorder=8,
                bbox=dict(boxstyle='square,pad=0.75', facecolor='#FAFAFA', edgecolor='none', alpha=0.96),
                arrowprops=dict(arrowstyle='-', color='#D7D7D7', linewidth=2.0,
                                shrinkA=0, shrinkB=0, connectionstyle='arc3,rad=0'))

label_color='#343434'
# Original numeric-label style: dark values placed immediately above or below each point.
main_offsets={
    'Virnig':(0,14),
    'Diamond Mower':(0,-20),
    'FAE Group':(0,-20),
    'Fecon':(0,14),
    'Loftness':(0,14),
}
for name in ['Virnig','Diamond Mower','FAE Group','Fecon','Loftness']:
    dx,dy=main_offsets[name]
    for i,v in enumerate(series[name]['v']):
        # Keep close crossings readable without changing the visual treatment.
        local_dx=dx
        if i==6 and name=='Virnig': local_dx=-11
        if i==6 and name=='Diamond Mower': local_dx=11
        ax.annotate(f'{v:,}',(x[i],v),xytext=(local_dx,dy),textcoords='offset points',
                    ha='center',va='center',fontsize=17,color=label_color,zorder=7)

# Near-zero series retain the same simple number labels, vertically staggered only where required.
small_specs={
    'Prinoth': list(enumerate(series['Prinoth']['v'])),
    'Mastodon': [(0,122),(6,79),(7,85)],
    'Shearex': [(6,85),(7,66)],
    'Denis Cimaf': [(5,91),(6,26),(7,22)],
}
small_offsets={'Prinoth':17,'Mastodon':-48,'Shearex':40,'Denis Cimaf':-78}
for name,specs in small_specs.items():
    for i,v in specs:
        ax.annotate(f'{v:,}',(x[i],series[name]['v'][i]),xytext=(0,small_offsets[name]),
                    textcoords='offset points',ha='center',va='center',fontsize=16,
                    color=label_color,zorder=7)

fig.savefig(OUT,dpi=100,facecolor='white')
print(OUT)
print('size_px',tuple(int(n) for n in fig.get_size_inches()*fig.dpi))
