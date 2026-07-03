import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'

// Faithful port of the original index.html three.js scene, using the vendored window.THREE
// (loaded via <script> in index.html) so behaviour is identical to the HTML version.
declare global { interface Window { THREE: any } }

export interface SceneHandle {
  setTail: (data: any) => void
  setView: (v: string) => void
  flyToDefect: (i: number) => void
}

const GRADE_SIZE: Record<string, number> = { minor: .6, major: .85, critical: 1.05, 'beyond-limit': 1.3, unknown: .7 }
const ACCENT = '#e0842a', CYAN = '#35e0d0', AMBER = '#f2a93b', RED = '#ff5b6a'

export default forwardRef<SceneHandle, { onDefectClick?: (i: number) => void }>(function ThreeScene(props, ref) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const api = useRef<any>({})

  useImperativeHandle(ref, () => ({
    setTail: (d: any) => api.current.setTail?.(d),
    setView: (v: string) => api.current.setView?.(v),
    flyToDefect: (i: number) => api.current.flyToDefect?.(i),
  }))

  useEffect(() => {
    const THREE = window.THREE
    if (!THREE) { console.error('THREE not loaded'); return }
    const canvas = canvasRef.current!
    const stage = canvas.parentElement as HTMLElement
    const THEME = document.documentElement.classList.contains('light') ? 'light' : 'dark'
    const SCENE = THEME === 'light'
      ? { fog: [0xe3e7ee, 0.008], env: ['#ffffff', '#eef1f6', '#dbe2ec'], floor: 0xe9edf3, grid: [0xccd2db, 0xe0e4ea], gridOp: 0.6, ink: '#3b434f', exposure: 1.0 }
      : { fog: [0x081019, 0.011], env: ['#43505f', '#1d2833', '#0b131c'], floor: 0x0a1119, grid: [0x2a3b4d, 0x18242f], gridOp: 0.55, ink: '#aab3c0', exposure: 1.02 }

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    renderer.outputEncoding = THREE.sRGBEncoding
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = SCENE.exposure
    renderer.physicallyCorrectLights = true
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap

    const scene = new THREE.Scene()
    scene.fog = new THREE.FogExp2(SCENE.fog[0], SCENE.fog[1])
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 200)
    camera.position.set(7.5, 3.9, 16.5)
    const controls = new THREE.OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true; controls.dampingFactor = .07
    controls.minDistance = 9; controls.maxDistance = 46
    controls.maxPolarAngle = Math.PI * 0.52; controls.target.set(0, 0, 0)
    controls.autoRotate = true; controls.autoRotateSpeed = 0.16

    function gradientTexture() {
      const c = document.createElement('canvas'); c.width = 16; c.height = 256
      const ctx = c.getContext('2d')!; const g = ctx.createLinearGradient(0, 0, 0, 256)
      g.addColorStop(0, SCENE.env[0] as string); g.addColorStop(.58, SCENE.env[1] as string); g.addColorStop(1, SCENE.env[2] as string)
      ctx.fillStyle = g; ctx.fillRect(0, 0, 16, 256)
      const t = new THREE.CanvasTexture(c); t.mapping = THREE.EquirectangularReflectionMapping; return t
    }
    try {
      const pmrem = new THREE.PMREMGenerator(renderer); pmrem.compileEquirectangularShader()
      const envTex = gradientTexture(); scene.environment = pmrem.fromEquirectangular(envTex).texture; envTex.dispose()
    } catch (e) { }

    scene.add(new THREE.HemisphereLight(0xffffff, 0xd6dce4, 1.05))
    const key = new THREE.DirectionalLight(0xffffff, 1.55); key.position.set(6, 11, 7)
    key.castShadow = true; key.shadow.mapSize.set(1024, 1024)
    key.shadow.camera.near = 1; key.shadow.camera.far = 50
    key.shadow.camera.left = -12; key.shadow.camera.right = 12; key.shadow.camera.top = 12; key.shadow.camera.bottom = -12
    key.shadow.bias = -0.0004; key.shadow.radius = 9; scene.add(key)
    const fill = new THREE.DirectionalLight(0xeaf0f8, 0.55); fill.position.set(-8, 3, 6); scene.add(fill)
    const rim = new THREE.DirectionalLight(0xffffff, 0.30); rim.position.set(2, 4, -9); scene.add(rim)

    const floor = new THREE.Mesh(new THREE.PlaneGeometry(140, 140),
      new THREE.MeshStandardMaterial({ color: SCENE.floor, metalness: 0.0, roughness: 0.92 }))
    floor.rotation.x = -Math.PI / 2; floor.position.y = -1.55; floor.receiveShadow = true; scene.add(floor)
    const grid = new THREE.GridHelper(64, 64, SCENE.grid[0], SCENE.grid[1]); grid.position.y = -1.548
    grid.material.transparent = true; grid.material.opacity = SCENE.gridOp; scene.add(grid)
    ; (function contactShadow() {
      const c = document.createElement('canvas'); c.width = c.height = 256
      const ctx = c.getContext('2d')!; const g = ctx.createRadialGradient(128, 128, 10, 128, 128, 124)
      g.addColorStop(0, 'rgba(0,0,0,.55)'); g.addColorStop(.5, 'rgba(0,0,0,.24)'); g.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = g; ctx.fillRect(0, 0, 256, 256)
      const m = new THREE.Mesh(new THREE.PlaneGeometry(14.5, 7),
        new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }))
      m.rotation.x = -Math.PI / 2; m.position.y = -1.535; scene.add(m)
    })()

    const FL = 10, R = 0.72
    const LIVERY = new THREE.Color('#aeb7c2')
    const plane = new THREE.Group(); scene.add(plane)
    const skinParts: any[] = []
    let modelReady = false

    // ---- model load ----
    ; (function loadAirframe() {
      const mtl = new THREE.MTLLoader(); mtl.setPath('/model-assets/')
      mtl.load('airplane.mtl', (materials: any) => {
        materials.preload()
        const loader = new THREE.OBJLoader(); loader.setMaterials(materials); loader.setPath('/model-assets/')
        loader.load('airplane.obj', (o: any) => {
          o.rotation.x = -Math.PI / 2; o.updateMatrixWorld(true)
          let box = new THREE.Box3().setFromObject(o); const size = new THREE.Vector3(); box.getSize(size)
          o.scale.setScalar((FL * 1.05) / Math.max(size.x, size.y, size.z)); o.updateMatrixWorld(true)
          box = new THREE.Box3().setFromObject(o); const c = new THREE.Vector3(); box.getCenter(c)
          o.position.sub(c); o.updateMatrixWorld(true)
          o.traverse((m: any) => {
            if (m.isMesh) {
              m.castShadow = true; m.receiveShadow = true
              const old = Array.isArray(m.material) ? m.material[0] : m.material
              const map = (old && old.map) || null; if (map) map.encoding = THREE.sRGBEncoding
              m.material = new THREE.MeshStandardMaterial({ map, color: map ? 0xffffff : 0xb7bec9, metalness: 0.18, roughness: 0.6, envMapIntensity: 0.95 })
              skinParts.push(m)
            }
          })
          plane.add(o); modelReady = true
          controls.target.set(0, 0, 0); controls.update()
          replaceHotspots()
          const lm = document.getElementById('loadmsg'); if (lm) lm.classList.add('gone')
        },
          (xhr: any) => { const lt = document.getElementById('loadtxt'); if (lt && xhr && xhr.lengthComputable) lt.textContent = 'Loading airframe… ' + (xhr.loaded / 1048576).toFixed(1) + '/' + (xhr.total / 1048576).toFixed(1) + ' MB' },
          () => { const lm = document.getElementById('loadmsg'); if (lm) { lm.classList.add('err'); const lt = document.getElementById('loadtxt'); if (lt) lt.textContent = '⚠ airframe model failed to load' } })
      }, undefined, () => { const lm = document.getElementById('loadmsg'); if (lm) { lm.classList.add('err'); const lt = document.getElementById('loadtxt'); if (lt) lt.textContent = '⚠ airframe materials failed to load' } })
    })()

    // ---- hotspots ----
    let hotspots: any[] = []; const raycaster = new THREE.Raycaster()
    const _probe = new THREE.Raycaster(); const _Z = new THREE.Vector3(0, 0, 1)
    let selectedDefects: any[] = []
    function glowSprite() {
      const c = document.createElement('canvas'); c.width = c.height = 128
      const ctx = c.getContext('2d')!; const g = ctx.createRadialGradient(64, 64, 2, 64, 64, 62)
      g.addColorStop(0, 'rgba(224,125,23,.92)'); g.addColorStop(.35, 'rgba(224,125,23,.5)')
      g.addColorStop(.7, 'rgba(224,125,23,.14)'); g.addColorStop(1, 'rgba(224,125,23,0)')
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(64, 64, 62, 0, 7); ctx.fill()
      return new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, depthTest: true }))
    }
    const segAngle = (loc: string) => { const n = parseInt((loc || '').replace(/\D/g, '')) || 0; return ((n % 12) / 12 - 0.5) * 2.1 }
    const defectX = (loc: string) => { const n = parseInt((loc || '').replace(/\D/g, '')) || 0; return 2.6 - (n % 12) * 0.5 }
    function _probeY(x: number, fromY: number, dir: number) {
      _probe.set(new THREE.Vector3(x, fromY, 0), new THREE.Vector3(0, dir, 0))
      const h = _probe.intersectObjects(skinParts, true)[0]; return h ? h.point.y : null
    }
    function fuselageAxisAt(x: number) {
      const top = _probeY(x, 60, -1), bot = _probeY(x, -60, 1)
      if (top == null || bot == null) return null
      return { y: (top + bot) / 2, r: Math.max((top - bot) / 2, 0.05) }
    }
    function skinPointFor(def: any) {
      const x = defectX(def.location), ang = segAngle(def.location)
      const dir = new THREE.Vector3(0, Math.cos(ang), Math.sin(ang)).normalize()
      const ax = modelReady && fuselageAxisAt(x)
      if (ax) {
        _probe.set(new THREE.Vector3(x, ax.y, 0), dir)
        const h = _probe.intersectObjects(skinParts, true)[0]
        if (h) { const nrm = h.face ? h.face.normal.clone().transformDirection(h.object.matrixWorld).normalize() : dir.clone(); return { pos: h.point.clone(), nrm } }
        return { pos: new THREE.Vector3(x, ax.y, 0).add(dir.clone().multiplyScalar(ax.r)), nrm: dir.clone() }
      }
      return { pos: new THREE.Vector3(x, Math.cos(ang) * R, Math.sin(ang) * R), nrm: dir.clone() }
    }
    function clearHotspots() { hotspots.forEach(h => plane.remove(h.grp)); hotspots = [] }
    function addHotspot(def: any) {
      const { pos, nrm } = skinPointFor(def)
      const sz = GRADE_SIZE[def.grade] || 0.7
      const grp = new THREE.Group(); grp.position.copy(pos).add(nrm.clone().multiplyScalar(0.012))
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.085 * sz + 0.02, 0.13 * sz + 0.03, 30),
        new THREE.MeshBasicMaterial({ color: ACCENT, transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false }))
      ring.quaternion.setFromUnitVectors(_Z, nrm.clone().normalize())
      const core = new THREE.Mesh(new THREE.SphereGeometry(0.045 * sz + 0.028, 18, 18),
        new THREE.MeshStandardMaterial({ color: ACCENT, emissive: ACCENT, emissiveIntensity: 1.3, metalness: 0.1, roughness: 0.45 }))
      const halo = glowSprite(); const base = 0.55 * sz + 0.26; halo.scale.setScalar(base)
      grp.add(ring); grp.add(core); grp.add(halo); plane.add(grp)
      hotspots.push({ grp, core, halo, ring, def, base, pos: grp.position.clone(), nrm })
    }
    function replaceHotspots() { clearHotspots(); selectedDefects.forEach(addHotspot) }

    // ---- health tint ----
    let tintTarget = LIVERY.clone(), attnNow = false, tintGlow = ACCENT
    function tintByHealth(h: number, grounded: boolean) {
      attnNow = grounded || (h != null && h < 40)
      tintGlow = grounded ? RED : ACCENT
      const mix = grounded ? 0.34 : 0.24
      tintTarget = attnNow ? LIVERY.clone().lerp(new THREE.Color(tintGlow), mix) : LIVERY.clone()
    }

    // ---- camera ----
    let flyTarget: any = null
    function flyTo(x: number, y: number, z: number) { flyTarget = new THREE.Vector3(x, y, z); controls.autoRotate = false }
    function setView(v: string) {
      controls.autoRotate = false
      if (v === 'top') camera.position.set(0.2, 20, 0.1)
      else if (v === 'side') camera.position.set(0.2, 1.6, 16)
      else { camera.position.set(4.5, 2.6, 11.5); controls.autoRotate = true }
    }

    // ---- picking ----
    renderer.domElement.addEventListener('pointerdown', (ev: PointerEvent) => {
      const r = renderer.domElement.getBoundingClientRect()
      const m = new THREE.Vector2(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1)
      raycaster.setFromCamera(m, camera)
      const hit = raycaster.intersectObjects(hotspots.map(h => h.core))[0]
      if (hit) { const hs = hotspots.find(h => h.core === hit.object); const i = selectedDefects.indexOf(hs.def); if (i >= 0) { focusDefect(i); props.onDefectClick?.(i) } }
    })
    renderer.domElement.addEventListener('pointermove', (ev: PointerEvent) => {
      const r = renderer.domElement.getBoundingClientRect()
      const m = new THREE.Vector2(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1)
      raycaster.setFromCamera(m, camera)
      renderer.domElement.style.cursor = raycaster.intersectObjects(hotspots.map(h => h.core)).length ? 'pointer' : 'grab'
    })
    controls.addEventListener('start', () => controls.autoRotate = false)
    function focusDefect(i: number) { hotspots.forEach((h, j) => h.selected = (j === i)); const h = hotspots[i]; if (h && h.pos) flyTo(h.pos.x, h.pos.y, h.pos.z) }

    // ---- resize ----
    function resize() {
      const w = stage.clientWidth, h = stage.clientHeight
      renderer.setSize(w, h, false); camera.aspect = w / h
      const occX = w > 940 ? 200 : 0
      const occY = h > 620 ? Math.round(h * 0.25) : 0
      camera.setViewOffset(w, h, occX, occY, w, h)
      camera.updateProjectionMatrix()
    }
    window.addEventListener('resize', resize); resize()

    // ---- animate ----
    let clock = 0, raf = 0
    ; (function animate() {
      raf = requestAnimationFrame(animate); clock += 0.016
      skinParts.forEach(m => {
        if (!m.material.map) m.material.color.lerp(tintTarget, 0.05)
        if (attnNow) { m.material.emissive.setStyle(tintGlow); m.material.emissiveIntensity = 0.06 + 0.05 * Math.sin(clock * 3) }
        else { m.material.emissiveIntensity *= 0.9 }
      })
      hotspots.forEach(h => {
        const sel = h.selected; const s = (sel ? 1.4 : 1) * (1 + 0.18 * Math.sin(clock * 3 + h.grp.position.x))
        h.halo.scale.setScalar(h.base * s); h.core.material.emissiveIntensity = sel ? 2.4 : 1.3
        if (h.ring) h.ring.material.opacity = sel ? 1 : 0.9
      })
      if (flyTarget) { controls.target.lerp(flyTarget, 0.08); if (controls.target.distanceTo(flyTarget) < 0.02) flyTarget = null }
      controls.update(); renderer.render(scene, camera)
    })()

    // ---- expose imperative API ----
    api.current.setTail = (t: any) => {
      selectedDefects = (t && t.defects) || []
      const st = (t && t.state) || {}
      tintByHealth(st.health ?? 100, !!st.grounded)
      replaceHotspots(); flyTo(0, 0, 0)
    }
    api.current.setView = setView
    api.current.flyToDefect = focusDefect

    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); renderer.dispose() }
  }, [])

  return <canvas id="canvas" ref={canvasRef} />
})
