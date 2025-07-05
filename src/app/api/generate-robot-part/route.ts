import { generateObject } from "ai"
import { groq } from "@ai-sdk/groq"
import { z } from "zod"

const RobotPartSchema = z.object({
    partFileName: z.string().describe("The filename of the part to add from the available parts list"),
    position: z.tuple([z.number(), z.number(), z.number()]).describe("3D position [x, y, z] where to place the part"),
    rotation: z.tuple([z.number(), z.number(), z.number()]).describe("3D rotation [x, y, z] in radians"),
    reasoning: z.string().describe("Brief explanation of why this part was chosen and positioned here"),
})

export async function POST(request: Request) {
    try {
        const { currentParts, uncondensedParts, condensedParts } = await request.json()

        const currentPartsDescription =
            currentParts.length === 0
                ? "No parts have been added yet"
                : currentParts
                    .map(
                        (part: any, index: number) =>
                            `Part ${index + 1}: ${part.fileName} position [${part.position.join(", ")}] rotation [${part.rotation.join(", ")}]`,
                    )
                    .join("\n")

        const prompt = `You are an AI agent designing FIRST Tech Challenge robots. Your task is to create a functionally simple robot by adding COTS parts one at a time to a 3D model.

CURRENT ROBOT STATE:
${currentPartsDescription}

AVAILABLE PARTS:
You have access to ${uncondensedParts.length} total robot parts from the following list:
${condensedParts.join("\n")}

DESIGN GUIDELINES:
- Focus on building the chassis + 4 mecanum wheels before adding other mechanisms
- Position coordinates: X (left/right), Y (up/down), Z (forward/back)
- Center robot around (0, 0, 0)
- Rotations in radians: 0=no rotation, π/2=90°, π=180°
- Ensure parts don't overlap unless intentionally connecting
- Maximum robot size is 450 x 450 x 450
- Utilize primarily UChannels for structure, do NOT place down a base plate

PART NAMING CONVENTIONS:
- Numbers precede letters, which indicate a dimensional or mechanical property: 
  - 6ID → 6mm inner diameter, 8OD → 8mm outer diameter, 96T → 96 teeth
  - 17H → 17 holes; 5x7H → 5 by 7 hole grid
- If ID is not specified, assume it is 8mm
- All standoffs are 6OD, all shafts are 8OD
- Holes are generally spaced 24mm apart
- All units are in millimeters

PART LIST CONDENSING FORMAT:
- Repeating part names with varying numeric components are compressed for brevity:
  - e.g.: 'Standoff:3-12,14-18x2' refers to 13 parts: Standoff3, Standoff4, ... Standoff12, Standoff14, Standoff16, Standoff18
  - e.g.: 'Spacer:6ID8OD2-8x2' = Spacer6ID8OD2, Spacer6ID8OD4, ... Spacer6ID8OD8
- The presence of an x2, x4, etc. means increments of 2, 4, etc. UNLESS the component is a plate, e.g. GridPlate3x5H just means GridPlate with size 3 by 5 holes
- Omit the colon when picking parts, e.g. with the range Standoff:3-12, you may pick Standoff5

POSITIONS SHOULD BE REASONABLY SIZED. FOR EXAMPLE, IF A PART HAS 96OD, THEN IT SHOULD BE AT LEAST 48 AWAY FROM OTHER PARTS!

Output a JSON array of next parts to add from the available parts list and position them realistically relative to existing parts.`

        console.log(prompt);

        const result = await generateObject({
            model: groq("llama-3.3-70b-versatile"),
            output: "array",
            schema: RobotPartSchema,
            prompt: prompt,
        })

        // Validate that the selected part exists in available parts
        result.object.forEach(part => {
            if (!uncondensedParts.includes(part.partFileName)) {
                throw new Error(`Selected part ${part.partFileName} is not available`)
            }
        })

        return Response.json(result.object)
    } catch (error) {
        console.error("Error generating robot part:", error)
        return Response.json({ error: "Failed to generate robot part" }, { status: 500 })
    }
}
