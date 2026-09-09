layout = "side_by_side";
phone_width = 76;
phone_thickness = 10;
earbuds_width = 65;
earbuds_thickness = 28;
clearance = 1.2;
base_thickness = 5;
slot_depth = 15;
phone_tilt_degrees = 15;
cable_hole_enabled = true;
cable_hole_diameter = 8;
wall = 3;
gap = 3;
base_depth = 55;
debug_cavity_envelope = false;

phone_module_width = phone_width + wall * 2;
earbuds_module_width = earbuds_width + wall * 2;
function cavity_depth(item_thickness) = item_thickness + clearance * 2;
function cavity_height() = slot_depth + 1;
function holder_depth(item_thickness, tilt) = max(
    base_depth,
    wall + cavity_height() * sin(tilt) + cavity_depth(item_thickness) * cos(tilt) + wall
);

phone_holder_depth = holder_depth(phone_thickness, phone_tilt_degrees);
earbuds_holder_depth = holder_depth(earbuds_thickness, 0);
base_width = layout == "side_by_side"
    ? phone_module_width + gap + earbuds_module_width
    : max(phone_module_width, earbuds_module_width);
total_depth = layout == "side_by_side"
    ? max(phone_holder_depth, earbuds_holder_depth)
    : phone_holder_depth + gap + earbuds_holder_depth;

module cavity(item_width, item_thickness, tilt) {
    translate([wall, wall + cavity_height() * sin(tilt), wall])
    rotate([tilt, 0, 0])
        cube([item_width, cavity_depth(item_thickness), cavity_height()]);
}

module slot_holder(x, y, item_width, item_thickness, tilt, depth) {
    translate([x, y, base_thickness])
    difference() {
        cube([
            item_width + wall * 2,
            depth,
            slot_depth
        ]);
        cavity(item_width, item_thickness, tilt);
    }
}

if (debug_cavity_envelope) {
    translate([0, 0, base_thickness])
        cavity(phone_width, phone_thickness, phone_tilt_degrees);
} else {
    difference() {
        union() {
            cube([base_width, total_depth, base_thickness]);
            slot_holder(0, 0, phone_width, phone_thickness, phone_tilt_degrees, phone_holder_depth);
            if (layout == "side_by_side")
                slot_holder(phone_module_width + gap, 0, earbuds_width, earbuds_thickness, 0, earbuds_holder_depth);
            else
                slot_holder(0, phone_holder_depth + gap, earbuds_width, earbuds_thickness, 0, earbuds_holder_depth);
        }
        if (cable_hole_enabled)
            translate([phone_module_width / 2, phone_holder_depth / 2, -1])
                cylinder(h=base_thickness + slot_depth + 2, d=cable_hole_diameter, $fn=48);
    }
}
