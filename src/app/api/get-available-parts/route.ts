import { readdir } from "fs/promises"
import { join } from "path"

export async function GET() {
    try {
        const glbDirectory = join(process.cwd(), "public", "glb")
        const files = await readdir(glbDirectory)

        const glbFiles = files.filter((file) => file.toLowerCase().endsWith(".glb"))

        return Response.json(glbFiles)
    } catch (error) {
        console.error("Error reading glb directory:", error)
        return Response.json({ error: "Failed to read parts directory" }, { status: 500 })
    }
}
