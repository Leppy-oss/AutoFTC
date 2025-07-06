import { generateObject } from "ai"
import { groq } from "@ai-sdk/groq"
import { z } from "zod"
import { readFileSync } from "fs"
import { join } from "path"

const llmName = "meta-llama/llama-4-maverick-17b-128e-instruct"

const StageOneSchema = z.object({
    name: z.string().describe("The name of the part to add from the available parts list"),
    reasoning: z.string().describe("Brief explanation of why this part was chosen and positioned here"),
})

const StageTwoSchema = z.object({
    name: z.string().describe("The name of the part to add from the available parts list"),
    position: z.tuple([z.number(), z.number(), z.number()]).describe("3D position [x, y, z] where to place the part"),
    rotation: z.tuple([z.number(), z.number(), z.number()]).describe("3D rotation [x, y, z] in radians"),
    reasoning: z.string().describe("Brief explanation of why this part was chosen and positioned here"),
})

export async function POST(request: Request) {
    try {
        const { currentParts, uncondensedParts, condensedParts } = await request.json()

        const currentPartsDescription =
            currentParts.length === 0 ? "No parts have been added yet" : currentParts.map(
                part => `${part.name.slice(0, -4)} corners ${part.minCorner.map((v: string) => parseFloat(v).toPrecision(2))} & ${part.maxCorner.map((v: string) => parseFloat(v).toPrecision(2))}`,
            ).join("\n")

        const stageOnePrompt = `You are an AI agent designing FIRST Tech Challenge robots. Your task is to create a functionally simple robot by adding COTS parts to a 3D model.

CURRENT ROBOT STATE:
${currentPartsDescription}

AVAILABLE PARTS:
You have access to ${uncondensedParts.length} total robot parts from the following list:
${condensedParts.join("\n")}

DESIGN GUIDELINES:
- Focus on building the chassis + 4 mecanum wheels before adding other mechanisms
- Center robot around (0, 0, 0) for (x, y, z) and treat y-axis as VERTICAL; x-/z-axes are HORIZONTAL
- All units are mm, all rotations are radians
- Maximum robot size is 450 x 450 x 450
- Ensure parts don't overlap unless intentionally connecting
- Do NOT place down a base plate
- Wheels must be arranged 2 on the left, 2 on the right
- The robot should have all 4 wheels touching the ground (x/y plane) and be oriented as such
- Focus on building structural components and do not add waste components. Use beams, plates, and PRIMARILY U-CHANNELS for structure, and QuadBlocks/DualBlocks for 90 degree mounting.
- Axially moving parts should be supported by bearings
- THE ROBOT CANNOT HAVE MORE THAN 4 WHEELS, 4 DRIVETRAIN MOTORS, 12 SERVOS, AND 4 OTHER MOTORS
- DO NOT WASTE TIME ADDING STANDOFFS!!!

PART NAMING CONVENTIONS:
- Numbers precede letters, which indicate a dimensional or mechanical property: 
  - 6ID → 6mm inner diameter, 8OD → 8mm outer diameter, 96T → 96 teeth
  - 17H → 17 holes; 5x7H → 5 by 7 hole grid
- If ID is not specified, assume it is 8mm
- All standoffs are 6OD, all shafts are 8OD
- Holes are generally spaced 24mm apart
- All units are in millimeters

PART LIST CONDENSING FORMAT:
- Repeating part names with varying numeric components are compressed for brevity
  - e.g.: 'Standoff:3-12,14-18x2' refers to 13 parts: Standoff3, Standoff4, ... Standoff12, Standoff14, Standoff16, Standoff18
  - e.g.: 'Spacer:6ID8OD2-8x2' = Spacer6ID8OD2, Spacer6ID8OD4, ... Spacer6ID8OD8
- The presence of an x2, x4, etc. means increments of 2, 4, etc. UNLESS the component is a plate, e.g. GridPlate3x5H just means GridPlate with size 3 by 5 holes
- Omit the colon when picking parts, e.g. with the range Standoff:3-12, you may pick Standoff5

Output the NAMES of the next parts to add from the available parts list, and specific information for each will be forwarded to you next.
MAKE SURE that the part names are VALID, e.g. do not output Standoff, output Standoff5 or Standoff3. Try to add as many parts at once AS POSSIBLE, and always place 4 wheels AT ONCE (2 left, 2 right).
NEVER place down only 1 wheel at once!
If inserting multiple parts of the same name, only output the name once and specify multiplicity in the reasoning.`

        // console.log(stageOnePrompt)

        const stageOneResult = await generateObject({
            model: groq(llmName),
            output: "array",
            mode: "json",
            schema: StageOneSchema,
            prompt: stageOnePrompt,
        })

        // Filter out parts with invalid names
        let filteredParts = stageOneResult.object.filter(part => uncondensedParts.includes(part.name))
        console.log(`Filtered out ${stageOneResult.object.length - filteredParts.length} s1 components with invalid names`)

        if (!filteredParts) return Response.json([])
        
        const stageOneParts = await Promise.all(filteredParts.map(async part => {
            let bbSize: [number, number, number] = [-1, -1, -1]
            let bbCenter: [number, number, number] = [-1, -1, -1]
            try {
                const jsonDirectory = join(process.cwd(), "public", "serialized", `${part.name}.json`)
                const data = JSON.parse(readFileSync(jsonDirectory, "utf8"))
                bbSize = data.bs
                bbCenter = data.bc
            }
            catch (e) {
                console.error(`Error reading JSON for ${part.name}`, e)
            }
            return {
                ...part,
                bbSize,
                bbCenter
            }
        }))

        const stageTwoPrompt = `You are an AI agent designing FIRST Tech Challenge robots. Your task is to create a functionally simple robot by adding COTS parts to a 3D model.

CURRENT ROBOT STATE:
${currentPartsDescription}

AVAILABLE PARTS:
You previously identified the following parts to be added, with certain bounding box sizes and reasoning to add them:
${stageOneParts.map(part => JSON.stringify(part)).join("\n")}

DESIGN GUIDELINES:
- Focus on building the chassis + 4 mecanum wheels before adding other mechanisms
- Center robot around (0, 0, 0) for (x, y, z) and treat y-axis as VERTICAL; x-/z-axes are HORIZONTAL
- All units are mm, all rotations are radians
- Maximum robot size is 450 x 450 x 450
- Ensure parts don't overlap unless intentionally connecting
- Wheels must be arranged 2 on the left, 2 on the right
- The robot should have all 4 wheels touching the ground (x/y plane) and be oriented as such
- Focus on building structural components and do not add waste components. Use beams, plates, and PRIMARILY U-CHANNELS for structure, and QuadBlocks/DualBlocks for 90 degree mounting.
- Axially moving parts should be supported by bearings
- Consider part orientation based on the bounding box data
  - Example: If the xy-plane dimensions are largest for a wheel's bounding box, then that is probably the axis containing the wheel's flat face.
  - Example: The longest axis of a beam, channel, etc. is the longest dimension, so it may need to be rotated to fulfill its objective as a structural component.
  - Rotate components 90 degrees in 1 or more axes to ensure their orientation fits!
- Ensure sufficient space between components that are on opposite sides of the drivetrain, e.g. wheels

PART NAMING CONVENTIONS:
- Numbers precede letters, which indicate a dimensional or mechanical property: 
  - 6ID → 6mm inner diameter, 8OD → 8mm outer diameter, 96T → 96 teeth
  - 17H → 17 holes; 5x7H → 5 by 7 hole grid
- If ID is not specified, assume it is 8mm
- All standoffs are 6OD, all shafts are 8OD
- Holes are generally spaced 24mm apart
- All units are in millimeters

PART LIST CONDENSING FORMAT:
- Repeating part names with varying numeric components are compressed for brevity
  - e.g.: 'Standoff:3-12,14-18x2' refers to 13 parts: Standoff3, Standoff4, ... Standoff12, Standoff14, Standoff16, Standoff18
  - e.g.: 'Spacer:6ID8OD2-8x2' = Spacer6ID8OD2, Spacer6ID8OD4, ... Spacer6ID8OD8
- The presence of an x2, x4, etc. means increments of 2, 4, etc. UNLESS the component is a plate, e.g. GridPlate3x5H just means GridPlate with size 3 by 5 holes
- Omit the colon when picking parts, e.g. with the range Standoff:3-12, you may pick Standoff5

POSITIONS SHOULD BE REASONABLY SIZED. FOR EXAMPLE, IF A PART HAS 96OD, THEN IT SHOULD BE AT LEAST 48 AWAY FROM OTHER PARTS!

Respond with ONLY a valid JSON array of next parts to add from the available parts list, and do NOT nest the JSON data within a subproperty, e.g. NO { "elements": [{...}]}.
Additionally, use ONLY precomputed numeric values — **do not use math expressions like 'Math.PI / 2 or 24 + 21 or 5.4 / 6'**. Do not include code blocks, backticks, or markdown. No explanations, no extra fields.

Output example:

[
  {
    "name": "SquareBeam29H",
    "position": [0, 112, 124.295],
    "rotation": [0, 0, 1.5708],
    "reasoning": "To stabilize the base frame..."
  },
  ...
]`
        
        // console.log(stageTwoPrompt)

        const stageTwoResult = await generateObject({
            model: groq(llmName),
            output: "array",
            mode: "json",
            schema: StageTwoSchema,
            prompt: stageTwoPrompt
        })
        // Filter out parts with invalid names
        filteredParts = stageTwoResult.object.filter(part => uncondensedParts.includes(part.name))
        console.log(`Filtered out ${stageTwoResult.object.length - filteredParts.length} s2 components with invalid names`)

        const stageTwoParts = stageTwoResult.object.map(part => {
            const mPart = stageOneParts.find(p => p.name == part.name)

            const minCorner = mPart? [
                part.position[0] + mPart.bbCenter[0] - mPart.bbSize[0] / 2,
                part.position[1] + mPart.bbCenter[1] - mPart.bbSize[1] / 2,
                part.position[2] + mPart.bbCenter[2] - mPart.bbSize[2] / 2
            ].map(v => v.toPrecision(2)) : [-1, -1, -1]

            const maxCorner = mPart? [
                part.position[0] + mPart.bbCenter[0] + mPart.bbSize[0] / 2,
                part.position[1] + mPart.bbCenter[1] + mPart.bbSize[1] / 2,
                part.position[2] + mPart.bbCenter[2] + mPart.bbSize[2] / 2
            ].map(v => v.toPrecision(2)) : [-1, -1, -1]

            return {
                ...mPart,
                ...part,
                minCorner,
                maxCorner
            }
        })

        return Response.json(stageTwoParts)
    } catch (error) {
        console.error("Error generating robot part:", error)
        return Response.json({ error: "Failed to generate robot part" }, { status: 500 })
    }
}