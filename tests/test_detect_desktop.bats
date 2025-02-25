#!/usr/bin/env bats

load '../data/scripts/detect_desktop'

# Tests for $XDG_CURRENT_DESKTOP
@test "Detect GNOME with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="GNOME"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "gnome" ]
}

@test "Detect Unity with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="Unity"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "unity" ]
}

@test "Detect KDE with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="KDE"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "kde" ]
}

@test "Detect XFCE with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="XFCE"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "xfce" ]
}

@test "Detect LXDE with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="LXDE"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "lxde" ]
}

@test "Detect LXQt with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="LXQt"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "lxqt" ]
}

@test "Detect MATE with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="MATE"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "mate" ]
}

@test "Detect Cinnamon with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="X-Cinnamon"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "cinnamon" ]
}

@test "Detect Lingmo with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="Lingmo"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "lingmo" ]
}

@test "Detect Deepin with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="Deepin"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "deepin" ]
}

@test "Detect Trinity with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="Trinity"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "trinity" ]
}

@test "Detect Fluxbox with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="Fluxbox"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "fluxbox" ]
}

@test "Detect Sway with XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="Sway"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "sway" ]
}

@test "Detect unknown XDG_CURRENT_DESKTOP" {
	XDG_CURRENT_DESKTOP="CustomDE"
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "customde" ]
}

# Tests for $DESKTOP_SESSION
@test "Detect GNOME with DESKTOP_SESSION" {
	unset XDG_CURRENT_DESKTOP
	DESKTOP_SESSION="gnome"
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "gnome" ]
}

@test "Detect Unity with DESKTOP_SESSION" {
	unset XDG_CURRENT_DESKTOP
	DESKTOP_SESSION="ubuntu"
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "unity" ]
}

@test "Detect Cinnamon with DESKTOP_SESSION" {
	unset XDG_CURRENT_DESKTOP
	DESKTOP_SESSION="cinnamon"
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "cinnamon" ]
}

@test "Detect XFCE with DESKTOP_SESSION" {
	unset XDG_CURRENT_DESKTOP
	DESKTOP_SESSION="xubuntu"
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "xfce" ]
}

@test "Detect LXDE with DESKTOP_SESSION" {
	unset XDG_CURRENT_DESKTOP
	DESKTOP_SESSION="lubuntu"
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "lxde" ]
}

@test "Detect Enlightenment with DESKTOP_SESSION" {
	unset XDG_CURRENT_DESKTOP
	DESKTOP_SESSION="enlightenment"
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "enlightenment" ]
}

@test "Detect Moksha with DESKTOP_SESSION" {
	unset XDG_CURRENT_DESKTOP
	DESKTOP_SESSION="moksha"
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "enlightenment" ]
}

@test "Detect Fluxbox with DESKTOP_SESSION" {
	unset XDG_CURRENT_DESKTOP
	DESKTOP_SESSION="fluxbox"
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "fluxbox" ]
}

@test "Detect unknown DESKTOP_SESSION" {
	unset XDG_CURRENT_DESKTOP
	DESKTOP_SESSION="otherde"
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "otherde" ]
}

# Special cases
@test "Detect KDE with KDE_FULL_SESSION" {
	unset XDG_CURRENT_DESKTOP
	unset DESKTOP_SESSION
	KDE_FULL_SESSION="true"
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "kde" ]
}

@test "Detect Awesome with XDG_SESSION_DESKTOP" {
	unset XDG_CURRENT_DESKTOP
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	XDG_SESSION_DESKTOP="awesome"
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "awesome" ]
}

@test "Detect Awesome with DESKTOP_STARTUP_ID" {
	unset XDG_CURRENT_DESKTOP
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	DESKTOP_STARTUP_ID="awesome"
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "awesome" ]
}

# Fallback
@test "Detect unknown when no variables set" {
	unset XDG_CURRENT_DESKTOP
	unset DESKTOP_SESSION
	unset KDE_FULL_SESSION
	unset XDG_SESSION_DESKTOP
	unset DESKTOP_STARTUP_ID
	run detect_desktop
	[ "$status" -eq 0 ]
	[ "$output" = "unknown" ]
}
