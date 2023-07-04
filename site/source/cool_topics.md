# Cool Topics in Ongoing Research
At any point, there are a huge number of topics
being researched in the ML+CV+Robotics communities. There
is some small subset of these that I find really interesting
and important, so I'll go over them here. If you ever want
to talk about any of these, feel free to reach out; I always
enjoy talking to people about cool new topics in the field.

## Fast Monocular SLAM
### Overview
Monocular Visual SLAM is a special case of the general problem of SLAM, a cornerstone problem in robotics and perception that I find interesting. Overall, SLAM(Simultaneous Localization and Mapping) is a problem that aims to allow a robot/agent to simultaneously **a) localize(determine position) in** and **b) map (determine the shape and nature of) the environment within which it operates.** This is quite a generic problem statement, and covers many different modalities and problem formulations.

Monocular V-SLAM is a special case of SLAM that aims to solve SLAM with only a series of images from a single camera. This problem variation is an important variation due to it only requiring a camera that can take images or record video frames; this is both useful due to it being applicable to environments with minimal sensors(like in underwater drones), and also because systems with more sensors, like IMUs, GPS sensors and magnetometers, can easily be addressed by adding more sub-systems to a lean, robust monocular SLAM system, which can use all the sensors in combination to get outstanding results.

### What I'm working on
At the moment, I'm working on a Monocular SLAM Framework that enables fast development of SLAM systems for the Monocular case. While it initially will only support Monocular V-SLAM, numerous design choices have been made to allow this framework to support arbitrary sensor modes to be added directly into the SLAM system, enabling the versatile expansion I alluded to above. I've been working on this system since around June 2023, and as of the time of writing, July 4th 2023, this system is almost done. I will post preliminary results on this site, and will later expand this system with the ability to train NeRFs and evaluate occupancy networks, which I go over below.

## Occupancy Networks

## NeRFs and 3D rendering

## Robotic Planning