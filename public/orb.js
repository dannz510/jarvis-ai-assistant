// orb.js — ASTRA Nebula WebGL Orb Visualizer
// Three.js r158+ | GPU-accelerated holographic neural orb
// Features: volumetric glow, energy rings, light sweep, node field,
//           mic-reactive ripples, particle orbit, FFT visualizer,
//           post-processing bloom + chromatic aberration

// ============================================================
//  Imports (CDN-loaded in index.html)
//  <script type="module" src="orb.js"></script>
//  Requires: three.min.js, OrbitControls.js,
//            UnrealBloomPass.js, EffectComposer.js,
//            FXAAShader.js, ChromaticAberrationShader.js
// ============================================================

// --- State Machine ---
const STATE_PROFILES = {
    idle:            { speed: 0.3,  intensity: 0.55, color: "#29d3f1" },
    listening:       { speed: 0.7,  intensity: 0.85, color: "#4cf4de" },
    user_paused:     { speed: 0.4,  intensity: 0.70, color: "#6f93b3" },
    processing:      { speed: 0.6,  intensity: 0.78, color: "#4bc0ff" },
    thinking:        { speed: 0.8,  intensity: 0.90, color: "#5cadff" },
    tool_selection:  { speed: 0.9,  intensity: 0.95, color: "#f1c26e" },
    executing:       { speed: 1.0,  intensity: 1.00, color: "#ffaa5e" },
    observing:       { speed: 0.5,  intensity: 0.80, color: "#68dcff" },
    responding:      { speed: 0.7,  intensity: 0.75, color: "#5de8de" },
    speaking:        { speed: 0.6,  intensity: 1.00, color: "#69efff" },
    success:         { speed: 0.5,  intensity: 1.00, color: "#6df2ab" },
    error:           { speed: 0.4,  intensity: 0.75, color: "#ff7571" },
    interrupted:     { speed: 0.7,  intensity: 0.85, color: "#ffd183" },
    waiting_for_clarification: { speed: 0.3, intensity: 0.68, color: "#f5c36e" },
    booting:         { speed: 0.6,  intensity: 0.85, color: "#63cdff" },
};

// ============================================================
//  OrbVisualizer
// ============================================================
export default class OrbVisualizer {
    constructor(canvasId, options = {}) {
        // --- DOM ---
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            throw new Error(`Canvas element #${canvasId} not found`);
        }

        // --- Config ---
        this.opts = Object.assign({
            antialias: true,
            alpha: true,
            premultipliedAlpha: false,
            powerPreference: "high-performance",
            nodeCount: 78,
            particleCount: 16,
            enablePostProcessing: true,
            maxFps: 60,
        }, options);

        // --- State ---
        this.state = "idle";
        this.audioLevel = 0.0;
        this.frequencyBands = { low: 0, mid: 0, high: 0 };
        this.progress = null;
        this.toolActivity = "";
        this.phase = 0.0;
        this.time = 0;
        this.deltaTime = 0.016;
        this.mouseX = 0.5;
        this.mouseY = 0.5;
        this.ripples = [];
        this.lastFrame = 0;

        // --- Three.js ---
        this._initRenderer();
        this._initScene();
        this._initCamera();
        this._initLights();
        this._initComposer();

        // --- Components ---
        this._buildGlow();
        this._buildNodeField();
        this._buildEnergyRings();
        this._buildLightSweep();
        this._buildParticles();
        this._buildFFTVisualizer();

        // --- Audio ---
        this.audioCtx = null;
        this.analyzer = null;
        this.microphone = null;
        this.audioStream = null;

        // --- Event listeners ---
        this._bindEvents();

        // --- Start ---
        this._animate();
    }

    // ============================================================
    //  Initialization
    // ============================================================

    _initRenderer() {
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: this.opts.antialias,
            alpha: this.opts.alpha,
            premultipliedAlpha: this.opts.premultipliedAlpha,
            powerPreference: this.opts.powerPreference,
        });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.0;
        this.renderer.sortObjects = false;
    }

    _initScene() {
        this.scene = new THREE.Scene();
        this.scene.background = null; // Transparent for blending

        // Starfield background
        this._buildStarfield();
    }

    _initCamera() {
        const aspect = this.canvas.clientWidth / this.canvas.clientHeight;
        this.camera = new THREE.PerspectiveCamera(30, aspect, 0.1, 1000);
        this.camera.position.set(0, 0, 8);

        this.cameraGroup = new THREE.Group();
        this.cameraGroup.add(this.camera);
        this.scene.add(this.cameraGroup);
    }

    _initLights() {
        // Ambient light
        const ambient = new THREE.AmbientLight(0x404060, 1.5);
        this.scene.add(ambient);

        // Dynamic point lights (for bloom effect)
        this.coreLight = new THREE.PointLight(0x3df5d9, 0.8, 5);
        this.coreLight.position.set(0, 0, 0);
        this.scene.add(this.coreLight);

        this.sweepLight = new THREE.PointLight(0x4df4ff, 0.4, 3);
        this.scene.add(this.sweepLight);
    }

    _initComposer() {
        if (!this.opts.enablePostProcessing) return;

        this.composer = new THREE.EffectComposer(this.renderer);
        this.composer.setSizeFromRenderer();

        // Bloom pass
        this.bloomPass = new UnrealBloomPass(
            new THREE.Vector2(this.canvas.clientWidth, this.canvas.clientHeight),
            1.2,   // strength
            0.7,   // radius
            0.3,   // threshold
        );
        this.composer.addPass(new THREE.RenderPass(this.scene, this.camera));
        this.composer.addPass(this.bloomPass);

        // FXAA
        const fxaaPass = new ShaderPass(FXAAShader);
        fxaaPass.uniforms["resolution"].value.set(
            1 / this.canvas.clientWidth,
            1 / this.canvas.clientHeight,
        );
        this.composer.addPass(fxaaPass);
    }

    _buildStarfield() {
        const geometry = new THREE.BufferGeometry();
        const vertices = [];
        const colors = [];

        for (let i = 0; i < 500; i++) {
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(Math.random() * 2 - 1);
            const radius = 15 + Math.random() * 10;
            const x = radius * Math.sin(phi) * Math.cos(theta);
            const y = radius * Math.sin(phi) * Math.sin(theta);
            const z = radius * Math.cos(phi);

            vertices.push(x, y, z);

            const twinkle = Math.random() * 0.5 + 0.5;
            colors.push(twinkle * 0.3, twinkle * 0.8, twinkle);
        }

        geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
        geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));

        const material = new THREE.PointsMaterial({
            size: 0.12,
            vertexColors: true,
            transparent: true,
            opacity: 0.5,
            sizeAttenuation: true,
        });

        this.starfield = new THREE.Points(geometry, material);
        this.scene.add(this.starfield);
    }

    _bindEvents() {
        // Mouse tracking for parallax
        this.canvas.addEventListener("mousemove", (e) => {
            const rect = this.canvas.getBoundingClientRect();
            this.mouseX = (e.clientX - rect.left) / rect.width;
            this.mouseY = (e.clientY - rect.top) / rect.height;
        });

        this.canvas.addEventListener("mouseleave", () => {
            this.mouseX = 0.5;
            this.mouseY = 0.5;
        });

        // Resize handling
        window.addEventListener("resize", () => {
            this._onResize();
        });
    }

    _onResize() {
        const w = this.canvas.clientWidth;
        const h = this.canvas.clientHeight;
        this.renderer.setSize(w, h);

        if (this.camera) {
            this.camera.aspect = w / h;
            this.camera.updateProjectionMatrix();
        }

        if (this.composer) {
            this.composer.setSize(w, h);
        }
    }

    // ============================================================
    //  Visual Layer Builders
    // ============================================================

    _buildGlow() {
        // Create a large sphere with additive blended glow shader
        const geometry = new THREE.SphereGeometry(5, 64, 64);

        const glowMaterial = new THREE.ShaderMaterial({
            uniforms: {
                color: { value: new THREE.Color(0x29d3f1) },
                intensity: { value: 0.55 },
                time: { value: 0 },
            },
            vertexShader: /* glsl */ `
                varying vec3 vNormal;
                varying vec3 vPosition;
                void main() {
                    vNormal = normalize(normalMatrix * normal);
                    vPosition = position;
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: /* glsl */ `
                uniform vec3 color;
                uniform float intensity;
                uniform float time;
                varying vec3 vNormal;
                varying vec3 vPosition;
                void main() {
                    float depth = length(vPosition) / 5.0;
                    float fresnel = pow(1.0 - dot(vNormal, vec3(0, 0, 1)), 3.0);
                    float pulse = 1.0 + 0.1 * sin(time * 2.0);
                    float alpha = fresnel * intensity * pulse * 0.5;
                    gl_FragColor = vec4(color, alpha);
                }
            `,
            transparent: true,
            side: THREE.BackSide,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
        });

        this.glowMesh = new THREE.Mesh(geometry, glowMaterial);
        this.scene.add(this.glowMesh);
    }

    _buildNodeField() {
        const count = this.opts.nodeCount;
        const goldenAngle = Math.PI * (3 - Math.sqrt(5));

        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);

        this.nodePositions = [];
        for (let i = 0; i < count; i++) {
            const y = 1 - 2 * (i + 0.5) / count;
            const ring = Math.sqrt(1 - y * y);
            const angle = i * goldenAngle;
            const x = Math.cos(angle) * ring;
            const z = Math.sin(angle) * ring;

            positions[i * 3] = x * 4;
            positions[i * 3 + 1] = y * 4;
            positions[i * 3 + 2] = z * 4;

            // Color: cyan with slight variation
            colors[i * 3] = 0.3;
            colors[i * 3 + 1] = 0.94;
            colors[i * 3 + 2] = 1.0;

            this.nodePositions.push({ x, y: y, z });
        }

        // Build links (Delaunay-like, distance-based)
        this.nodeLinks = [];
        const threshold = 0.26;
        for (let i = 0; i < count; i++) {
            for (let j = i + 1; j < count; j++) {
                const dx = this.nodePositions[i].x - this.nodePositions[j].x;
                const dy = this.nodePositions[i].y - this.nodePositions[j].y;
                const dz = this.nodePositions[i].z - this.nodePositions[j].z;
                const dist = dx * dx + dy * dy + dz * dz;
                if (dist < threshold) {
                    this.nodeLinks.push({ a: i, b: j });
                }
            }
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));

        const material = new THREE.PointsMaterial({
            size: 0.08,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            sizeAttenuation: true,
            blending: THREE.AdditiveBlending,
        });

        this.nodeField = new THREE.Points(geometry, material);
        this.scene.add(this.nodeField);
    }

    _buildEnergyRings() {
        this.energyRings = [];
        const ringData = [
            { radius: 5.4, rotationDirection: 0.012, color: 0x29d3f1, opacity: 0.4 },
            { radius: 6.6, rotationDirection: -0.018, color: 0x3df5d9, opacity: 0.3 },
            { radius: 7.8, rotationDirection: 0.009, color: 0x9d7bff, opacity: 0.2 },
        ];

        for (let i = 0; i < ringData.length; i++) {
            const data = ringData[i];
            const geometry = new THREE.RingGeometry(
                data.radius - 0.05, data.radius + 0.05, 128,
            );

            const material = new THREE.LineBasicMaterial({
                color: data.color,
                transparent: true,
                opacity: data.opacity,
                blending: THREE.AdditiveBlending,
                side: THREE.DoubleSide,
            });

            const ring = new THREE.LineLoop(geometry, material);
            ring.rotation.x = Math.PI / 2;
            ring.userData = { ...data };
            this.scene.add(ring);
            this.energyRings.push(ring);
        }
    }

    _buildLightSweep() {
        // Sweep is a shader-based arc rendered on the core sphere
        // Using a transparent plane with conic gradient texture
        const geometry = new THREE.PlaneGeometry(9, 9);

        const sweepMaterial = new THREE.ShaderMaterial({
            uniforms: {
                time: { value: 0 },
                color: { value: new THREE.Color(0x29d3f1) },
                intensity: { value: 1.0 },
            },
            transparent: true,
            side: THREE.DoubleSide,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
            vertexShader: /* glsl */ `
                varying vec2 vUv;
                void main() {
                    vUv = uv;
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: /* glsl */ `
                uniform float time;
                uniform vec3 color;
                uniform float intensity;
                varying vec2 vUv;
                void main() {
                    vec2 center = vec2(0.5, 0.5);
                    vec2 dir = vUv - center;
                    float angle = atan(dir.y, dir.x);
                    float dist = length(dir);
                    float sweep = mod(angle + time * 2.0, 6.2832) / 6.2832;
                    float sweepGlow = smoothstep(0.0, 0.15, sweep) * (1.0 - smoothstep(0.15, 0.30, sweep));
                    float outer = smoothstep(0.0, 0.3, dist) * (1.0 - smoothstep(0.7, 1.0, dist));
                    float alpha = sweepGlow * outer * intensity * 0.8;
                    gl_FragColor = vec4(color, alpha);
                }
            `,
        });

        this.sweepPlane = new THREE.Mesh(geometry, sweepMaterial);
        this.sweepPlane.renderOrder = 5;
        this.scene.add(this.sweepPlane);
    }

    _buildParticles() {
        const count = this.opts.particleCount;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(count * 3);
        const sizes = new Float32Array(count);

        this.particleData = [];
        for (let i = 0; i < count; i++) {
            const angle = Math.random() * Math.PI * 2;
            const radiusRatio = 0.85 + Math.random() * 0.2;
            const speed = 0.012 + Math.random() * 0.012;
            const phase = Math.random() * Math.PI * 2;
            const orbitR = 0.04 + Math.random() * 0.08;
            const size = 0.8 + Math.random() * 1.8;

            positions[i * 3] = 0;
            positions[i * 3 + 1] = 0;
            positions[i * 3 + 2] = 0;

            sizes[i] = size;

            this.particleData.push({ angle, radiusRatio, speed, phase, orbitR });
        }

        geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));

        const material = new THREE.ShaderMaterial({
            uniforms: {
                color: { value: new THREE.Color(0x4df4ff) },
                map: { value: this._createSpriteTexture() },
            },
            vertexShader: /* glsl */ `
                attribute float size;
                varying float vSize;
                void main() {
                    vSize = size;
                    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                    gl_PointSize = size * (300.0 / -mvPosition.z);
                    gl_Position = projectionMatrix * mvPosition;
                }
            `,
            fragmentShader: /* glsl */ `
                uniform vec3 color;
                uniform sampler2D map;
                varying float vSize;
                void main() {
                    vec4 texColor = texture2D(map, gl_PointCoord);
                    if (texColor.a < 0.1) discard;
                    gl_FragColor = vec4(color, texColor.a);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        this.particleSystem = new THREE.Points(geometry, material);
        this.scene.add(this.particleSystem);
    }

    _createSpriteTexture() {
        const canvas = document.createElement("canvas");
        canvas.width = 32;
        canvas.height = 32;
        const ctx = canvas.getContext("2d");
        const gradient = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
        gradient.addColorStop(0, "rgba(255,255,255,1.0)");
        gradient.addColorStop(0.3, "rgba(77, 244, 255,0.6)");
        gradient.addColorStop(1, "rgba(77, 244, 255,0.0)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 32, 32);

        const texture = new THREE.CanvasTexture(canvas);
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;
        return texture;
    }

    _buildFFTVisualizer() {
        // Not needed in WebGL — handled by node field reactivity
        // This method placeholder for future expansion
    }

    // ============================================================
    //  Public API
    // ============================================================

    setContextState(state) {
        if (STATE_PROFILES[state]) {
            this.state = state;
            this._updateModeColors();
        }
    }

    setState(state) {
        // Alias for compatibility
        this.setContextState(state);
    }

    setAudioLevel(level, bands = null) {
        this.audioLevel = Math.max(0, Math.min(1, level));
        if (bands) {
            this.frequencyBands = {
                low: bands.low || 0,
                mid: bands.mid || 0,
                high: bands.high || 0,
            };
        } else {
            this.frequencyBands = {
                low: this.audioLevel,
                mid: this.audioLevel * 0.7,
                high: this.audioLevel * 0.4,
            };
        }
    }

    triggerPulse() {
        this.phase += Math.PI / 2;
    }

    triggerSuccess() {
        this.setContextState("success");
        this.triggerPulse();
    }

    triggerError() {
        this.setContextState("error");
        this.triggerPulse();
    }

    setProgress(value) {
        this.progress = value !== null ? Math.max(0, Math.min(1, value)) : null;
    }

    setToolActivity(toolName) {
        this.toolActivity = toolName || "";
        this.setContextState("executing");
    }

    interrupt() {
        this.setContextState("interrupted");
    }

    reset() {
        this.setContextState("idle");
        this.audioLevel = 0;
        this.frequencyBands = { low: 0, mid: 0, high: 0 };
        this.ripples = [];
        this.progress = null;
        this.toolActivity = "";
    }

    // ============================================================
    //  Audio
    // ============================================================

    async startMicrophone() {
        try {
            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });

            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const source = this.audioCtx.createMediaStreamSource(this.audioStream);
            this.analyzer = this.audioCtx.createAnalyser();
            this.analyzer.fftSize = 1024;
            this.analyzer.smoothingTimeConstant = 0.8;

            source.connect(this.analyzer);
            this._audioData = new Float32Array(this.analyzer.frequencyBinCount);

            return true;
        } catch (err) {
            console.error("Microphone access failed:", err);
            return false;
        }
    }

    stopMicrophone() {
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(t => t.stop());
            this.audioStream = null;
        }
        if (this.audioCtx) {
            this.audioCtx.close();
            this.audioCtx = null;
        }
    }

    _updateAudio() {
        if (!this.analyzer) return;

        this.analyzer.getByteFrequencyData(this._frequencyData);

        const binCount = this.analyzer.frequencyBinCount;
        const lowEnd = Math.floor(binCount * 0.1);
        const midEnd = Math.floor(binCount * 0.5);
        const highEnd = binCount;

        let lowSum = 0, midSum = 0, highSum = 0;
        for (let i = 0; i < lowEnd; i++) lowSum += this._frequencyData[i];
        for (let i = lowEnd; i < midEnd; i++) midSum += this._frequencyData[i];
        for (let i = midEnd; i < highEnd; i++) highSum += this._frequencyData[i];

        const lowAvg = lowSum / (lowEnd * 255) || 0;
        const midAvg = midSum / ((midEnd - lowEnd) * 255) || 0;
        const highAvg = highSum / ((highEnd - midEnd) * 255) || 0;

        this.frequencyBands = {
            low: lowAvg,
            mid: midAvg,
            high: highAvg,
        };
        this.audioLevel = Math.max(lowAvg, midAvg, highAvg);

        // Spawn ripple on voice activity
        if (this.audioLevel > 0.15 && Math.random() < 0.2) {
            this._spawnRipple();
        }
    }

    _spawnRipple() {
        this.ripples.push({
            radius: 0.8,
            alpha: 200,
            speed: 0.03 + this.audioLevel * 0.02,
        });
    }

    // ============================================================
    //  Mode updates
    // ============================================================

    _updateModeColors() {
        const profile = STATE_PROFILES[this.state] || STATE_PROFILES.idle;
        const color = new THREE.Color(profile.color);

        if (this.glowMesh) {
            this.glowMesh.material.uniforms.color.value = color;
            this.glowMesh.material.uniforms.intensity.value = profile.intensity;
        }

        if (this.coreLight) {
            this.coreLight.color = color;
        }

        if (this.sweepPlane) {
            this.sweepPlane.material.uniforms.color.value = color;
            this.sweepPlane.material.uniforms.intensity.value = profile.intensity;
        }

        if (this.energyRings) {
            this.energyRings.forEach((ring, i) => {
                ring.material.color = color.clone().lerp(new THREE.Color(0x9d7bff), i * 0.1);
                ring.material.opacity = (0.2 + i * 0.1) * profile.intensity;
            });
        }
    }

    // ============================================================
    //  Animation Loop
    // ============================================================

    _animate() {
        const now = performance.now() * 0.001;
        this.deltaTime = Math.min(0.05, now - this.time);
        this.time = now;
        this.phase += this.deltaTime * (STATE_PROFILES[this.state]?.speed || 0.3);

        // Update audio
        this._updateAudio();

        // Update glow
        if (this.glowMesh) {
            this.glowMesh.material.uniforms.time.value = this.time;
        }

        // Update node field rotation
        if (this.nodeField) {
            this.nodeField.rotation.y += this.deltaTime * 0.08;
            this.nodeField.rotation.x = Math.sin(this.time * 0.3) * 0.05;
        }

        // Update energy rings
        this.energyRings.forEach((ring, i) => {
            const dir = ring.userData.rotationDirection;
            const profile = STATE_PROFILES[this.state] || STATE_PROFILES.idle;
            ring.rotation.z += dir * this.deltaTime * (1 + profile.intensity);
        });

        // Update light sweep
        if (this.sweepPlane) {
            this.sweepPlane.material.uniforms.time.value = this.time + this.phase * 0.5;
        }

        // Update particles
        this._updateParticles();

        // Update ripples
        this._updateRipples();

        // Mouse parallax (subtle camera tilt)
        const targetX = (this.mouseX - 0.5) * 0.2;
        const targetY = (this.mouseY - 0.5) * 0.2;
        this.cameraGroup.rotation.y += (targetX - this.cameraGroup.rotation.y) * 0.02;
        this.cameraGroup.rotation.x += (targetY - this.cameraGroup.rotation.x) * 0.02;

        // Update core light
        if (this.coreLight) {
            const intensity = (STATE_PROFILES[this.state]?.intensity || 0.55) * (1 + this.audioLevel);
            this.coreLight.intensity = 0.8 + intensity * 0.8;
        }

        // Render
        if (this.composer) {
            this.composer.render();
        } else {
            this.renderer.render(this.scene, this.camera);
        }

        requestAnimationFrame(() => this._animate());
    }

    _updateParticles() {
        if (!this.particleSystem) return;

        const positions = this.particleSystem.geometry.attributes.position.array;
        const time = this.time + this.phase;

        for (let i = 0; i < this.opts.particleCount; i++) {
            const data = this.particleData[i];
            const orbitAngle = time * data.speed + data.phase;
            const orbitR = data.orbitR;

            const x = Math.cos(orbitAngle) * 4 * data.radiusRatio +
                      Math.cos(orbitAngle + Math.PI / 2) * 4 * orbitR;
            const y = Math.sin(orbitAngle) * 4 * data.radiusRatio * 0.55 +
                      Math.sin(orbitAngle + Math.PI / 2) * 4 * orbitR * 0.55;

            positions[i * 3] = x;
            positions[i * 3 + 1] = y;
            positions[i * 3 + 2] = Math.sin(orbitAngle) * 4 * 0.1;
        }

        this.particleSystem.geometry.attributes.position.needsUpdate = true;
    }

    _updateRipples() {
        // Ripples are rendered via fragment shader in WebGL version
        // Placeholder for future ring mesh expansion
        for (let i = this.ripples.length - 1; i >= 0; i--) {
            const ripple = this.ripples[i];
            ripple.radius += ripple.speed;
            ripple.alpha -= 1.5;

            if (ripple.alpha <= 0) {
                this.ripples.splice(i, 1);
            }
        }
    }

    // ============================================================
    //  Public Methods
    // ============================================================

    getStatus() {
        return {
            state: this.state,
            audioLevel: this.audioLevel,
            frequencyBands: this.frequencyBands,
            progress: this.progress,
            toolActivity: this.toolActivity,
        };
    }

    resize() {
        this._onResize();
    }

    dispose() {
        this.stopMicrophone();
        if (this.renderer) this.renderer.dispose();
        if (this.composer) this.composer.dispose();
    }
}

// ============================================================
//  Module Exports
// ============================================================
export {
    OrbVisualizer,
    STATE_PROFILES,
};