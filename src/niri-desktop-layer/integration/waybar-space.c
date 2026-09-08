/* Waybar CFFI v2: retain the exclusive zone until the CSS fade completes.
 * ABI: Waybar 0.15.0 include/modules/cffi.hpp. No worker thread or polling.
 */
#include <gtk/gtk.h>
#include <gtk-layer-shell.h>

typedef struct wbcffi_module wbcffi_module;
typedef struct {
    wbcffi_module *obj;
    const char *waybar_version;
    GtkContainer *(*get_root_widget)(wbcffi_module *);
    void (*queue_update)(wbcffi_module *);
} wbcffi_init_info;
typedef struct { const char *key, *value; } wbcffi_config_entry;

typedef struct {
    GtkWidget *root;
    GtkWindow *window;
    GtkStyleContext *style;
    gulong handler;
    guint sync, release;
    int hidden;
} Space;

#ifdef SPACE_TEST
static void release_zone(GtkWindow *window);
#else
static void release_zone(GtkWindow *window) {
    gtk_layer_set_exclusive_zone(window, 0);
    gtk_layer_try_force_commit(window);
}
#endif

static void cancel(guint *source) {
    if (*source) { g_source_remove(*source); *source = 0; }
}

static gboolean release_space(gpointer data) {
    Space *self = data;
    self->release = 0;
    if (self->window && gtk_style_context_has_class(gtk_widget_get_style_context(GTK_WIDGET(self->window)), "mode-invisible"))
        release_zone(self->window);
    return G_SOURCE_REMOVE;
}

static gboolean sync_state(gpointer data) {
    Space *self = data;
    self->sync = 0;
    if (!self->window) return G_SOURCE_REMOVE;
    int hidden = gtk_style_context_has_class(gtk_widget_get_style_context(GTK_WIDGET(self->window)), "mode-invisible");
    if (hidden == self->hidden) return G_SOURCE_REMOVE;
    cancel(&self->release);
    if (hidden) {
        if (self->hidden < 0) release_zone(self->window);
        else self->release = g_timeout_add(240, release_space, self);
    }
    /* The normal Waybar mode restores automatic reservation before fade-in. */
    self->hidden = hidden;
    return G_SOURCE_REMOVE;
}

static void changed(GtkStyleContext *style, gpointer data) {
    (void)style;
    Space *self = data;
    /* Defer until Waybar has finished applying the new mode. */
    if (!self->sync) self->sync = g_idle_add(sync_state, self);
}

static gboolean attach(gpointer data) {
    Space *self = data;
    self->sync = 0;
    GtkWidget *top = gtk_widget_get_toplevel(self->root);
    if (!GTK_IS_WINDOW(top)) return G_SOURCE_REMOVE;
    self->window = GTK_WINDOW(top);
    g_object_add_weak_pointer(G_OBJECT(top), (gpointer *)&self->window);
    /* The content box opacity actually changes; the window style may not. */
    GtkWidget *content = gtk_bin_get_child(GTK_BIN(top));
    self->style = g_object_ref(gtk_widget_get_style_context(content));
    self->handler = g_signal_connect(self->style, "changed", G_CALLBACK(changed), self);
    return sync_state(self);
}

const size_t wbcffi_version = 2;
void *wbcffi_init(const wbcffi_init_info *info,
                  const wbcffi_config_entry *entries, size_t count) {
    (void)entries; (void)count;
    Space *self = g_new0(Space, 1);
    self->hidden = -1;
    self->root = GTK_WIDGET(info->get_root_widget(info->obj));
    /* This is a controller, not a visible module; it adds no spacing. */
    gtk_widget_set_no_show_all(self->root, TRUE);
    gtk_widget_hide(self->root);
    self->sync = g_idle_add(attach, self);
    return self;
}

void wbcffi_deinit(void *instance) {
    Space *self = instance;
    cancel(&self->sync);
    cancel(&self->release);
    if (self->style) {
        g_signal_handler_disconnect(self->style, self->handler);
        g_object_unref(self->style);
    }
    if (self->window)
        g_object_remove_weak_pointer(G_OBJECT(self->window), (gpointer *)&self->window);
    g_free(self);
}
