set(key_sources)
if(CONFIG_IDF_TARGET_ESP32S31 AND CONFIG_METALIO_EARLY_POWER_KEY)
    if(CONFIG_BOOTLOADER_SKIP_VALIDATE_ALWAYS OR CONFIG_BOOTLOADER_SKIP_VALIDATE_ON_POWER_ON)
        message(FATAL_ERROR "Early-key handoff requires the SDK's complete image validation")
    endif()
    list(APPEND key_sources "hooks.c")
endif()
idf_component_register(SRCS ${key_sources}
    INCLUDE_DIRS "../../components/metalio_hw/include"
    REQUIRES bootloader_support esp_hal_gpio esp_rom soc spi_flash esp_app_format)
if(CONFIG_METALIO_EARLY_POWER_KEY)
    target_link_options(${COMPONENT_LIB} INTERFACE "-Wl,--wrap=bootloader_load_image")
endif()

