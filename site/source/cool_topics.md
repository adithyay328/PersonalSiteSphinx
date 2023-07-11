# Cool Topics in Ongoing Research
At any point, there are a huge number of topics
being researched in the ML+CV+Robotics communities. There
is some small subset of these that I find interesting
and important, so I'll give a brief overview of them
here. If you ever want to talk about any of these, feel 
free to reach out; I always enjoy talking to people about 
cool new topics in the field.

## Fast Monocular SLAM
### Overview
Monocular Visual SLAM is a special case of the general problem of SLAM, a cornerstone problem in robotics and perception that I find interesting. Overall, SLAM(Simultaneous Localization and Mapping) is a problem that aims to allow a robot/agent to simultaneously **a) localize(determine position) in** and **b) map (determine the shape and nature of) the environment within which it operates.** This is quite a generic problem statement and covers many different modalities and problem formulations.

Monocular V-SLAM is a special case of SLAM that aims to solve SLAM with only a series of images from a single camera. This problem variation is an important variation due to it only requiring a camera that can take images or record video frames; this is both useful due to it applying to environments with minimal sensors(like in underwater drones), and also because systems with more sensors, like IMUs, GPS sensors, and magnetometers, can easily be addressed by adding more sub-systems to a lean, robust monocular SLAM system, which can use all the sensors in combination to get outstanding results.

### What I'm working on
At the moment, I'm working on a Monocular SLAM Framework that enables fast development of SLAM systems for the Monocular case. While it initially will only support Monocular V-SLAM, numerous design choices have been made to allow this framework to support arbitrary sensor modes to be added directly into the SLAM system, enabling the versatile expansion I alluded to above. I've been working on this system since around June 2023, and as of the time of writing, July 4th, 2023, this system is almost done. I will post preliminary results on this site, and will later expand this system with the ability to train NeRFs and evaluate occupancy networks, which I go over below.

### Future Problems I'm interested in
#### Moving Objects
Monocular SLAM, in and of itself, is a somewhat solved problem, with strong approaches shown by the current SOTA, which include ORB-SLAM on the in-direct side, and DroidSLAM + Deep Path VO on the "direct-ish" side.

One problem area that hasn't been approached with strong results, however, is Monocular SLAM with modeling of motion in the world; the 2 SLAM systems above are somewhat robust to dynamic environments, mainly by using optimization and association steps that remove outliers, which catch most instances of fast-moving objects in them. 

Neither, however, detect motion in the scene(DROID does to some extent with its flow estimates), and neither does anything in the realm of actually estimating the kinematics of visible objects. These are both problems I'm looking into, and I'm experimenting with different approaches that might work for this important special case of Mono-SLAM.

#### Better Initialization for Online Indirect Systems
Another interesting set of improvements to the SOTA includes finding better ways to initialize Monocular Systems. As mentioned in COLMAP, ORB-SLAM, and other photogrammetry-based localization papers, initialization is a rather important step of a reconstruction pipeline, with a bad choice being extremely detrimental to the long-term success of the system. 

In offline systems like COLMAP, heuristics are run across the entire frame graph, with a decision made with the entire map's basic connectivity known before the selection. In online systems, however, the size and nature of the map are not known, and so a choice of initialization point may be suboptimal if initialization is done too early; this is something that systems like ORB-SLAM and OV2-SLAM deal with by using robust initialization, and hoping a good point is selected.

One problem I'm looking into is whether better choices can be made by re-initializing the graph against a better point of initialization if found after running the system for a while, and at the same time whether learning-based initializers can outperform statistical initialization methods like the one used in ORB-SLAM.

## Occupancy Networks
### Overview
Occupancy networks are a cool paradigm for scene representation, popularized a lot by Tesla's recent use of them in their self-driving systems(note though, the idea predates Tesla's use). Tesla's use of this tech is documented quite nicely in their presentations at [WAD@CPVR 2022](https://www.youtube.com/watch?v=jPCV4GKX9Dw) and [WAD@CPVR 2023](https://www.youtube.com/watch?v=6x-Xb_uT7ts), and I would recommend anyone interested to watch through the important parts of these videos to get some cool insights from their team.

### Connection with NeRFs
There exists a pretty well-known connection between the output of an Occupany Network, which is a voxel storing occupancy probabilities and optionally other semantics, and the representation implied by NeRFs; this is made readily apparent if you focus in on the "volume density" aspect of a NeRF, which is similar to the occupancy probability emitted by an Occupancy Network.

Due to this, a rather interesting line of inquiry is whether we could use one to augment the other; I'm working on some problems in this area, but I won't go too deep into it until I get my work to a finalized state.

### The Value of Occupancy Networks
To summarize Tesla's nice explainers on Occupancy Nets, this scene representation has numerous advantages that make it quite nice to use in a variety of use cases:
- Can be readily converted into an SDF/TSDF/ESDF(signed distance function), which are easily and frequently used representations of the environment for robotic planning algorithms
- Are easy to interpret, making operation more transparent than the latent space generated by end -> end NeRFs
- First-order time-derivatives and higher order derivatives of the occupancy of a voxel in the world can be computed using outputted occupancy voxels across timeframes, following alignment(shift both occupancy voxels to be aligned correctly)
- As shown with Tesla's Optimus Robot, **this scene representation can be re-used across the self-driving and robotics domains**. This is an important feature for me since I'm interested in creating general perception systems, and this is an exciting result from that standpoint