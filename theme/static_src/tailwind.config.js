module.exports = {
  content: [
    // Templates de Django
    '../templates/**/*.html',
    '../../templates/**/*.html',
    '../../**/templates/**/*.html',
    
    // Si tienes JS con clases de Tailwind
    '../../static/js/**/*.js',
  ],
  
  theme: {
    extend: {
      // Puedes agregar colores personalizados aquí
      colors: {
        // 'brand-blue': '#1da1f2',
      },
    },
  },
  
  plugins: [
    require('daisyui'),
  ],
  
  daisyui: {
    themes: [
      "light",
      "dark",
      "cupcake",
      "corporate",
      "synthwave",
      // Puedes elegir los themes que quieras
    ],
    darkTheme: "dark", // Tema oscuro por defecto
    base: true, // Aplica estilos base
    styled: true, // Aplica estilos a componentes
    utils: true, // Agrega utility classes
    prefix: "", // Prefijo para clases (vacío = sin prefijo)
    logs: true, // Muestra info en consola
  },
}
