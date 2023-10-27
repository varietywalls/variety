#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <wayland-client-core.h>
#include <wayland-client-protocol.h>
#include <wayland-client.h>


void geometry(void* data, struct wl_output* wl_output, int x, int y, int physical_width, int physical_height, int subpixel, const char* make, const char* model, int transform){};
void mode(void* data, struct wl_output* wl_output, uint flags, int width, int height, int refresh){}; 
void done(void* data, struct wl_output* wl_output){};
void scale(void* data, struct wl_output* wl_output, int factor){};
void description(void* data, struct wl_output* wl_output, const char *name){}
void name(void* data, struct wl_output* wl_output, const char* name){
  fprintf(stdout,"%s\n", name);
};


static const struct wl_output_listener outlist = {
 .done = done,
 .geometry = geometry,
 .mode = mode,
 .name = name,
 .scale = scale,
 .description = description
};
void global(void *data, struct wl_registry* registery, uint name, const char* iface, uint ver){
  if (strcmp("wl_output", iface)==0)
  {
    struct wl_output *output = (struct wl_output *)wl_registry_bind(registery, name, &wl_output_interface, 4);
    wl_output_add_listener(output, &outlist,  NULL);
    wl_display_dispatch(data);
  }
};

void global_remove(void* data, struct wl_registry* wl_registry, uint name) {

}
static const struct wl_registry_listener listener = {
	global,
	global_remove
};
int main(int argc, char *argv[]){
  struct wl_display *display = wl_display_connect(NULL);
  struct wl_registry *registry = wl_display_get_registry(display);
  wl_registry_add_listener(registry, &listener, display);
  wl_display_dispatch(display);
};
