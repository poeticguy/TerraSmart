export default {
  async fetch() {
    return new Response("Hola desde TerraSmart 👋\n", {
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
}
