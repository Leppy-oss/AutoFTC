"use client"

import { Canvas } from "@react-three/fiber"
import { OrbitControls, Environment, Grid } from "@react-three/drei"
import { Suspense } from "react"
import { useGLTF } from "@react-three/drei"
import {
    BoxGeometry,
    MeshStandardMaterial,
    EdgesGeometry,
    LineBasicMaterial,
    LineSegments,
    BufferGeometry,
    Group
} from "three"
import { useMemo } from "react"
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils"

export interface RobotPart {
    id: string
    name: string
    bbSize: [number, number, number]
    bbCenter: [number, number, number]
    position: [number, number, number]
    rotation: [number, number, number]
    minCorner: [number, number, number]
    maxCorner: [number, number, number]
}

interface RobotPartProps {
    part: RobotPart
}

function RobotPartComponent({ part }: RobotPartProps) {
    const { scene } = useGLTF(`/glb/${part.name}`)
    const merged = useMemo(() => {
        const geometries: BufferGeometry[] = []
        const group = new Group()

        scene.traverse((child: any) => {
            if (child.isMesh) {
                child.material = new MeshStandardMaterial({ color: part.name.includes("Wheel") ? 0x000000 : 0x708090 })
                child.updateMatrix()
                const geom = child.geometry.clone()
                geom.applyMatrix4(child.matrix)
                geometries.push(geom)
            }
        })
        group.add(scene.clone())

        if (!part.name.includes("Wheel")) {
            const mergedGeometry = mergeGeometries(geometries, false)
            const edges = new EdgesGeometry(mergedGeometry, 80)
            const lines = new LineSegments(
                edges,
                new LineBasicMaterial({ color: 0x696969 })
            )
            group.add(lines)
        }

        const bb = new LineSegments(
            new EdgesGeometry(new BoxGeometry(part.bbSize[0], part.bbSize[1], part.bbSize[2])),
            new LineBasicMaterial({ color: 0x66cdaa })
        )

        group.add(bb)

        bb.position.set(
            part.position[0] + part.bbCenter[0],
            part.position[1] + part.bbCenter[1],
            part.position[2] + part.bbCenter[2]
        )

        return group
    }, [scene])

    return (
        <primitive
            object={merged}
            position={part.position}
            rotation={part.rotation}
            scale={0.01}
        />
    )
}

function Scene({ parts }: { parts: RobotPart[] }) {
    return (
        <>
            <ambientLight intensity={0.4} />

            {parts.map((part) => (
                <RobotPartComponent key={part.id} part={part} />
            ))}

            <Grid
                args={[15, 15]}
                position={[0, 0, 0]}
                cellColor="#6b7280"
                sectionSize={7.5}
                sectionThickness={1}
                sectionColor="#374151"
                fadeDistance={15}
                fadeStrength={0.6}
            />
        </>
    )
}

function LoadingFallback() {
    return (
        <group position={[0, 0, 0]}>
            <mesh position={[0, 0, 0]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#ff5c00" />
            </mesh>
            <lineSegments>
                <edgesGeometry attach="geometry" args={[new BoxGeometry(1, 1, 1)]} />
                <lineBasicMaterial attach="material" color="#ab4900" />
            </lineSegments>
        </group>
    )
}

export default function RobotViewer({ parts }: { parts: RobotPart[] }) {
    return (
        <div className="w-full h-full bg-gradient-to-b from-slate-100 to-slate-200 rounded-lg overflow-hidden">
            <Canvas camera={{ position: [3, 3, 3], fov: 60, near: 0.01, far: 50 }} shadows>
                <Suspense fallback={<LoadingFallback />}>
                    <Scene parts={parts} />
                    <Environment preset="studio" />
                    <OrbitControls enablePan={true} enableZoom={true} enableRotate={true} enableDamping={true} />
                </Suspense>
            </Canvas>
        </div>
    )
}
