"use client"

import { useState, useEffect, Fragment } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2, Play, Plus, RotateCcw, Search } from "lucide-react"
import { Input } from "@/components/ui/input"
import RobotViewer from "@/components/viewer"
import { RobotPart } from "@/components/viewer"

interface AIResponsePart {
  partFileName: string
  position: [number, number, number]
  rotation: [number, number, number]
  reasoning: string
}

type AIResponse = AIResponsePart[]

export default function RobotDesigner() {
  const [robotParts, setRobotParts] = useState<RobotPart[]>([])
  const [availableParts, setAvailableParts] = useState<string[]>([])
  const [isLoadingParts, setIsLoadingParts] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationStep, setGenerationStep] = useState(0)
  const [lastAIReasoning, setLastAIReasoning] = useState<string>("")
  const [partsFilter, setPartsFilter] = useState("")
  const [partsError, setPartsError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAvailableParts = async () => {
      try {
        setIsLoadingParts(true)
        setPartsError(null)
        const response = await fetch("/api/get-available-parts")

        if (!response.ok) {
          throw new Error("Failed to fetch available parts")
        }

        const parts = await response.json()
        setAvailableParts(parts)
        setRobotParts([])
        setRobotParts([{
          id: "test",
          fileName: "ssc.glb",
          position: [0, 0, 0],
          rotation: [0, 0, 0]
        },
        {
          id: "test2",
          fileName: "ClampCollar6ID.glb",
          position: [0, 0, 0],
          rotation: [0, 0, 0]
        }])
      } catch (error) {
        console.error("Error fetching parts:", error)
        setPartsError("Failed to load available parts. Please refresh the page.")
      } finally {
        setIsLoadingParts(false)
      }
    }

    fetchAvailableParts()
  }, [])

  const condensePartList = (parts: string[]) => {
    function tokenize(part) {
      return part.match(/(\d+|\D+)/g);
    }

    // Condense numbers into ranges (step 1, 2, or 4 with len >= 3)
    function condenseNumbers(nums: number[]) {
      nums = Array.from(new Set(nums)).sort((a, b) => a - b);

      const result = [];
      let i = 0;

      while (i < nums.length) {
        let start = nums[i];
        let j = i + 1;
        let step = null;

        while (j < nums.length) {
          const diff = nums[j] - nums[j - 1];
          if (step === null) step = diff;
          if (diff !== step) break;
          j++;
        }

        const count = j - i;

        if ((step <= 4) && count >= 3) {
          result.push(`${start}-${nums[j - 1]}${step === 1 ? '' : `x${step}`}`);
        } else {
          for (let k = i; k < j; k++) {
            result.push(nums[k].toString());
          }
        }

        i = j;
      }

      return result;
    }

    // Group parts by prefix (before first number)
    function groupByPrefix(parts) {
      const groups = {};

      for (const part of parts) {
        const tokens = tokenize(part);
        let prefix = '';
        for (const t of tokens) {
          if (/\d/.test(t)) break;
          prefix += t;
        }

        if (!groups[prefix]) groups[prefix] = [];
        groups[prefix].push(part);
      }

      return groups;
    }

    // Cartesian product
    function cartesian(arrays) {
      return arrays.reduce((acc, curr) => {
        const res = [];
        acc.forEach(a => {
          curr.forEach(b => {
            res.push(a.concat([b]));
          });
        });
        return res;
      }, [[]]);
    }

    function condenseGroup(parts) {
      if (parts.length <= 1) return parts;

      const first = parts[0];
      const prefixMatch = first.match(/^[^\d]+/);
      const prefix = prefixMatch ? prefixMatch[0] : '';

      // Get suffixes by stripping the shared prefix
      const suffixes = parts.map(p => p.slice(prefix.length));

      // If ANY suffix contains an "x", skip numeric condensing
      if (suffixes.some(s => s.includes('x'))) {
        const sorted = suffixes.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
        return [prefix + sorted.join(',')];
      }

      // Tokenize suffixes
      const tokenized = suffixes.map(s => s.match(/(\d+|\D+)/g));
      const tokenCount = tokenized[0].length;
      const isNumberToken = [];

      for (let i = 0; i < tokenCount; i++) {
        isNumberToken.push(tokenized.every(tokens => /^\d+$/.test(tokens[i])));
      }

      const staticTokens = [];
      const numbersAtIndex = [];

      for (let i = 0; i < tokenCount; i++) {
        if (isNumberToken[i]) {
          const nums = tokenized.map(tokens => parseInt(tokens[i], 10));
          numbersAtIndex[i] = condenseNumbers(nums);
          staticTokens[i] = null;
        } else {
          staticTokens[i] = tokenized[0][i];
          numbersAtIndex[i] = null;
        }
      }

      const arraysForCartesian = staticTokens.map((tok, i) =>
        tok !== null ? [tok] : numbersAtIndex[i]
      );

      const combos = cartesian(arraysForCartesian);
      const condensedParts = combos.map(tokens => prefix + tokens.join(''));

      const sharedPrefix = findLongestSharedPrefix(condensedParts);
      const shortened = condensedParts.map(p => p.slice(sharedPrefix.length));

      return [sharedPrefix + ":" + shortened.join(',')];
    }

    // Find longest shared string prefix in array
    function findLongestSharedPrefix(strings) {
      if (strings.length === 0) return '';
      let prefix = strings[0];
      for (let i = 1; i < strings.length; i++) {
        while (!strings[i].startsWith(prefix)) {
          prefix = prefix.slice(0, -1);
          if (prefix === '') return '';
        }
      }
      return prefix;
    }

    const groups = groupByPrefix(parts);
    const outputLines = [];

    for (const groupParts of Object.values(groups)) {
      const condensed = condenseGroup(groupParts);
      outputLines.push(condensed.join(' '));
    }

    return outputLines;
  }

  const generateNextPart = async () => {
    if (availableParts.length === 0) {
      console.error("No available parts loaded")
      return
    }

    const uncondensedParts = availableParts.map(p => p.slice(0, -4)); // slice off .glb suffix
    const condensedParts = condensePartList(uncondensedParts);

    setIsGenerating(true)

    try {
      const response = await fetch("/api/generate-robot-part", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          currentParts: structuredClone(robotParts).map(
            part => ({
              ...part,
              position: [part.position[0] * 100, part.position[1] * 100, part.position[2] * 100]
            })
          ),
          uncondensedParts,
          condensedParts
        }),
      })

      if (!response.ok) {
        throw new Error("Failed to generate part")
      }

      const aiResponse: AIResponse = await response.json()

      const newParts: RobotPart[] = aiResponse.map((part) => ({
        id: `part_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        fileName: part.partFileName + ".glb",
        position: [part.position[0] / 100, part.position[1] / 100, part.position[2] / 100],
        rotation: part.rotation,
      }))

      setRobotParts((prev) => [...prev, ...newParts])

      // Combine reasoning from all parts, e.g. join with newlines or just take first
      const combinedReasoning = aiResponse.map(p => p.reasoning).join("\n")
      setLastAIReasoning(combinedReasoning)

      setGenerationStep((prev) => prev + 1)
    } catch (error) {
      console.error("Error generating part:", error)
    } finally {
      setIsGenerating(false)
    }
  }

  const resetDesign = () => {
    setRobotParts([])
    setGenerationStep(0)
    setLastAIReasoning("")
  }

  const startGeneration = () => {
    if (robotParts.length === 0 && availableParts.length > 0) {
      generateNextPart()
    }
  }

  const filteredParts = availableParts.filter((part) => part.toLowerCase().includes(partsFilter.toLowerCase()))

  const canGenerate = !isLoadingParts && availableParts.length > 0 && !isGenerating

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">AutoFTC - Next Gen CADding</h1>
          <p className="text-slate-600 text-lg">Design FIRST Tech Challenge robots with generative AI</p>
        </div>

        {partsError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{partsError}</p>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card className="h-[600px]">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center justify-between">
                  <span>3D Robot Viewer</span>
                  <Badge variant="secondary">{robotParts.length} Parts</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="h-[520px] p-3">
                <RobotViewer parts={robotParts} />
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Generation Controls</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {robotParts.length === 0 ? (
                  <Button onClick={startGeneration} disabled={!canGenerate} className="w-full" size="lg">
                    {isLoadingParts ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Loading Parts...
                      </>
                    ) : isGenerating ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-2" />
                        Start Robot Generation
                      </>
                    )}
                  </Button>
                ) : (
                  <div className="space-y-3">
                    <Button onClick={generateNextPart} disabled={!canGenerate} className="w-full" size="lg">
                      {isGenerating ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Adding Part...
                        </>
                      ) : (
                        <>
                          <Plus className="w-4 h-4 mr-2" />
                          Add Next Part
                        </>
                      )}
                    </Button>

                    <Button onClick={resetDesign} variant="outline" className="w-full bg-transparent">
                      <RotateCcw className="w-4 h-4 mr-2" />
                      Reset Design
                    </Button>
                  </div>
                )}

                <div className="text-sm text-slate-600 space-y-1">
                  <div>
                    <strong>Step:</strong> {generationStep}
                  </div>
                  <div>
                    <strong>Available Parts:</strong> {availableParts.length}
                  </div>
                </div>
              </CardContent>
            </Card>

            {lastAIReasoning && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">AI Reasoning</CardTitle>
                </CardHeader>
                <CardContent>
                  {
                    lastAIReasoning.split("\n").map((rsn, idx) => 
                      <Fragment key={idx}>
                        <p className="text-sm text-slate-600 leading-relaxed">{rsn}</p>
                        <br />
                      </Fragment>
                    )
                  }
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Current Parts</CardTitle>
              </CardHeader>
              <CardContent>
                {robotParts.length === 0 ? (
                  <p className="text-sm text-slate-500 italic">No parts added yet</p>
                ) : (
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {robotParts.map((part, index) => (
                      <div key={part.id} className="flex items-center justify-between text-xs">
                        <span className="font-mono truncate">{`${part.fileName}\t${part.position}`}</span>
                        <Badge variant="outline" className="text-xs">
                          #{index + 1}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center justify-between">
                  Available Parts
                  <Badge variant="secondary" className="text-xs">
                    {availableParts.length}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Search parts..."
                    value={partsFilter}
                    onChange={(e) => setPartsFilter(e.target.value)}
                    className="pl-8 text-xs"
                  />
                </div>

                {isLoadingParts ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                ) : (
                  <div className="max-h-40 overflow-y-auto">
                    {filteredParts.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">
                        {partsFilter ? "No parts match your search" : "No parts available"}
                      </p>
                    ) : (
                      <div className="grid grid-cols-1 gap-1">
                        {filteredParts.slice(0, 50).map((part) => (
                          <div key={part} className="text-xs font-mono text-slate-600 truncate">
                            {part}
                          </div>
                        ))}
                        {filteredParts.length > 50 && (
                          <div className="text-xs text-slate-400 italic">... and {filteredParts.length - 50} more</div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
