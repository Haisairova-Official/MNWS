use std::{collections::HashMap, path::PathBuf, sync::LazyLock};

use regex::Regex;
use waybar_cffi::gtk::{
    self as gtk, CssProvider,
    prelude::{CssProviderExt, StyleContextExt, WidgetExt},
};

thread_local! {
    static MENU_PROVIDER: CssProvider = {
        let provider = CssProvider::new();
        if let Some(screen) = gtk::gdk::Screen::default() {
            gtk::StyleContext::add_provider_for_screen(
                &screen, &provider, gtk::STYLE_PROVIDER_PRIORITY_USER,
            );
        }
        provider
    };
}

static COLOR_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"@define-color\s+([\w-]+)\s+([^;]+);").expect("valid color regex")
});
static FONT_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"font-family\s*:\s*([^;}]+);").expect("valid font regex"));

fn waybar_config_file(name: &str) -> Option<PathBuf> {
    let home = std::env::var("HOME").ok()?;
    let path = PathBuf::from(home).join(".config/waybar").join(name);
    path.is_file().then_some(path)
}

fn read_colors() -> HashMap<String, String> {
    let mut colors = HashMap::new();
    let Some(path) = waybar_config_file("colors.css") else {
        return colors;
    };
    let Ok(text) = std::fs::read_to_string(path) else {
        return colors;
    };
    for captures in COLOR_RE.captures_iter(&text) {
        let name = captures
            .get(1)
            .map(|m| m.as_str().trim())
            .unwrap_or_default();
        let value = captures
            .get(2)
            .map(|m| m.as_str().trim())
            .unwrap_or_default();
        if !name.is_empty() && !value.is_empty() {
            colors.insert(name.to_string(), value.to_string());
        }
    }
    colors
}

fn read_font_family() -> Option<String> {
    let path = waybar_config_file("style-bottom.css")?;
    let text = std::fs::read_to_string(path).ok()?;
    // 样式文件后面出现的 font-family 会覆盖前面的，取最后一段的第一族字体。
    let captures = FONT_RE.captures_iter(&text).last()?;
    let value = captures.get(1)?.as_str();
    let family = value.split(',').next()?.trim().trim_matches('"').trim();
    (!family.is_empty()).then(|| family.to_string())
}

/// 让菜单使用与底部任务栏一致的 matugen 调色板（每次弹出重读 colors.css）。
pub fn apply(menu: &gtk::Menu) {
    let colors = read_colors();
    fn pick<'a>(colors: &'a HashMap<String, String>, name: &str, fallback: &'a str) -> &'a str {
        colors.get(name).map(String::as_str).unwrap_or(fallback)
    }
    let background = pick(&colors, "surface_container_high", "#282934");
    let foreground = pick(&colors, "on_surface", "#e2e1ef");
    let hover = pick(&colors, "surface_container", "#1e1f29");
    let outline = pick(&colors, "outline_variant", "#454651");

    let font_family = read_font_family();
    let font_css = match font_family {
        Some(family) => format!("font-family: \"{}\";", family.replace('"', "")),
        None => String::new(),
    };

    let css = format!(
        "menu.mnws-menu {{\n\
             background-color: {background};\n\
             color: {foreground};\n\
             {font_css}\n\
             padding: 4px;\n\
             margin: 4px;\n\
             border-radius: 9px;\n\
             border: none;\n\
             box-shadow: none;\n\
             background-image: none;\n\
         }}\n\
         menu.mnws-menu menuitem {{\n\
             color: {foreground};\n\
             padding: 5px 12px;\n\
             min-height: 16px;\n\
             border-radius: 9px;\n\
         }}\n\
         menu.mnws-menu menuitem:hover,\n\
         menu.mnws-menu menuitem:selected {{\n\
             background-color: {hover};\n\
             color: {foreground};\n\
             border-radius: 9px;\n\
         }}\n\
         menu.mnws-menu separator {{\n\
             background-color: {outline};\n\
             margin: 6px 0;\n\
         }}\n\
         window.mnws-menu-popup, window.mnws-menu-popup decoration {{\n\
             background-color: transparent;\n\
             background-image: none;\n\
             border: none;\n\
             box-shadow: none;\n\
         }}\n"
    );

    MENU_PROVIDER.with(|provider| {
        if let Err(error) = provider.load_from_data(css.as_bytes()) {
            tracing::warn!(%error, "menu palette CSS parse error");
        }
    });
    // Screen-scoped selectors also reach menu items and the popup decoration;
    // a provider attached to the menu widget alone does not style those nodes.
    menu.style_context().add_class("mnws-menu");
    if let Some(top) = menu.toplevel() {
        top.style_context().add_class("mnws-menu-popup");
    }
    menu.connect_realize(|menu| {
        if let Some(top) = menu.toplevel() {
            top.style_context().add_class("mnws-menu-popup");
        }
    });
}
