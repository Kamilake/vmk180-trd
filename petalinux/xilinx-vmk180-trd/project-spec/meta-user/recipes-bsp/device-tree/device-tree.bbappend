FILESEXTRAPATHS_prepend := "${THISDIR}/files:${SYSCONFIG_PATH}:"

SRC_URI += "file://config \
	 	file://system-user.dtsi \
		file://ina226-power-monitor.dtsi \
		file://pl-custom.dtsi \
		file://single-capture.dtsi \ 
		file://display.dtsi \
		file://pcie.dtsi" 

python () {
    if d.getVar("CONFIG_DISABLE"):
        d.setVarFlag("do_configure", "noexec", "1")
}

export PETALINUX
do_configure_append () {
	script="${PETALINUX}/etc/hsm/scripts/petalinux_hsm_bridge.tcl"
	data=${PETALINUX}/etc/hsm/data/
	eval xsct -sdx -nodisp ${script} -c ${WORKDIR}/config \
	-hdf ${DT_FILES_PATH}/hardware_description.${HDF_EXT} -repo ${S} \
	-data ${data} -sw ${DT_FILES_PATH} -o ${DT_FILES_PATH} -a "soc_mapping"
}