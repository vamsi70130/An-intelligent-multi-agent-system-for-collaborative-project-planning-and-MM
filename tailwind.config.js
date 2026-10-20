/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0E1116",
        surface: "#1C212B",
        surfaceRaised: "#242B38",
        paper: "#F5F4F0",
        slate: "#8B93A7",
        line: "#2A3140",
        violet: "#6E56CF",
        violetSoft: "#8673DB",
        amber: "#D9A441",
        green: "#5EB08C",
        red: "#D9694F",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        body: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
}
