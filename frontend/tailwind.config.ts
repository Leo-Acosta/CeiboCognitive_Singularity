import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        core: {
          ink: "#09111f",
          panel: "#101a2e",
          cyan: "#23d9ff",
          amber: "#ffbf47",
          green: "#45f5a5",
        },
      },
    },
  },
  plugins: [],
};

export default config;
