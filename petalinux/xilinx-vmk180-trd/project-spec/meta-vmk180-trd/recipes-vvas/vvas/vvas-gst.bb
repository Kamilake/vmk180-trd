SUMMARY = "VVAS gst"
DESCRIPTION = "VVAS gstreamer plugins for VVAS SDK"
SECTION = "multimedia"
LICENSE = "Apache-2.0 & LGPLv2 & MIT & BSD-3-Clause"

include vvas.inc
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://0001-vvas-xfilter-dynamic-config.patch"

DEPENDS = "glib-2.0 glib-2.0-native xrt libcap libxml2 bison-native flex-native gstreamer1.0 jansson vvas-utils"

RDEPENDS:${PN} = "gstreamer1.0-plugins-base"

inherit meson pkgconfig gettext

S = "${WORKDIR}/git/vvas-gst-plugins"

GIR_MESON_ENABLE_FLAG = "enabled"
GIR_MESON_DISABLE_FLAG = "disabled"

FILES:${PN} += "${libdir}/gstreamer-1.0/*.so"
FILES:${PN}-dev += "${libdir}/gstreamer-1.0/*.a ${libdir}/gstreamer-1.0/include"

#CVE_PRODUCT = "gstreamer"
