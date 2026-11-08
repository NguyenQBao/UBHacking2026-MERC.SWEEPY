# Sources, dependencies and scope

This repository collects the project's code, parametric CAD sources, STL files, drawings and guides. No new open-source licence has been chosen for the project; third-party libraries, images and datasets keep their own terms and are not relicensed here.

## Official hardware images and wiring references

The Raspberry Pi 4B photo and 40-pin header image in `hardware/wiring` come from Raspberry Pi; the SunFounder module photos come from SunFounder's official documentation. The wiring table and drawing layout are this project's connection plan; the official images do not certify it.

- https://www.raspberrypi.com/products/raspberry-pi-4-model-b/
- https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- https://docs.sunfounder.com/projects/3in1-kit-v2/en/latest/components/component_l298n_module.html
- https://www.st.com/resource/en/datasheet/l298.pdf

Personal photos, web screenshots and chat attachments shared during the project are not included. The robot concept image in `docs/concept` is a design sketch, not evidence of the assembled car.

## Software and printing references

- Ultralytics: https://docs.ultralytics.com/ — training uses 8.4.194, under its AGPL-3.0 or commercial licence.
- OpenCV: https://docs.opencv.org/ — image processing, ground homography and calibration.
- Picamera2: https://github.com/raspberrypi/picamera2
- GPIO Zero: https://gpiozero.readthedocs.io/en/stable/api_output.html
- Prusa: https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135
- Arducam OV5647 module reference: https://www.arducam.com/raspberry-pi-camera/

CAD dependencies and versions are in each folder's requirements and source files.

## Datasets

The repository holds no copies of third-party training images or annotations, no team training photos and no weights. The TACO conversion report keeps the source annotation hash, categories and licence metadata. Check image and dataset terms at the source; the code licence does not cover the photos.

- https://github.com/pedropro/TACO
- https://ai.bu.edu/zerowaste/
- https://github.com/garythung/trashnet

When the files were first imported, local machine paths were replaced by repository paths and private LAN addresses by `raspberrypi.local`; to run the services, use the device's real address or an SSH tunnel.
