# Switchblade

**Switchblade** is a small tool to send SVG files to plotters for vinyl cutting.  
It’s deliberately reduced to the basics: open an SVG, reload the file, plot it.  
There’s also support for rotating 90° and adding a frame around your design for easier vinyl removal.

The workflow is simple: set up your scene in Inkscape, save the plot file, and send it to the plotter.  
There’s also a scale value, so you can scale up the scene—these plotters can easily handle files several meters long. With careful vinyl alignment, even 10-meter plots are feasible.

---

## Technical Details

Switchblade is written in Python, so it’s cross-platform. The releases include binaries for Linux, macOS, and Windows. Running the source on FreeBSD should work as well.


You can find the latest releases [here](https://github.com/joergbeigang/switchblade/releases).

---

## Motivation

I’ve had a Mimaki CG101 plotter for over 5 years. It came from my parents’ company, and when they closed it down, this was the one piece of equipment I couldn’t sell. The original software was old and required a parallel-port dongle—not something I wanted on my network.

I tried using Inkscape’s plotting function via a USB-serial adapter—an utterly frustrating experience. Precision was poor, and any curve was cut painfully slowly.

Luckily, a USB-serial adapter works both ways. I was able to hook up the old computer to my workstation and capture the data being sent to the plotter. Feeding that data to an AI helped me figure out the parameters of the flattening algorithm. In minutes, I had a working solution. From there, it was mostly connecting `pyserial`, parsing SVGs, and compensating for the drag knife.

The goal is simple: make old professional plotters usable today. Brands like Mimaki or Roland are built to last, and replacement parts like knives or rubber rolls are still available.

---

## Compatibility

So far, I’ve only tested Switchblade with my Mimaki CG101 because it’s the only plotter I have access to. That said, it should work with other plotters as well—it’s just HPGL.

---

## Usage

- Make sure everything in your SVG is a **path**—no text or other primitives.  
- Best practice: group everything in one group. Avoid negative scaling.  
  - In Inkscape: drag-select all → `Ctrl+Shift+G` to ungroup → `Ctrl+G` to group → save.

### Keyboard Shortcuts

- `Ctrl+O` → Open SVG  
- `Ctrl+R` → Reload file  
- `Ctrl+P` → Plot  
- `Ctrl+,` → Settings dialog

The GUI is straightforward and mostly self-explanatory.

---

## Final Notes

This is a personal project and not polished commercial software.  
I hope it can be useful for others, and maybe inspire someone to pick up an old professional plotter instead of a cheap new model.

You can download binaries or check out the latest release [here](https://github.com/yourusername/switchblade/releases).
